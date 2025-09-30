# app/endpoints.py

import io  # For in-memory file handling
import asyncio
from datetime import timedelta
from datetime import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from PyPDF2 import PdfReader, PdfWriter  # For handling PDF pages
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from .. import auth, crud
from ..config import settings
from ..database import get_db
from ..limiter import limiter  # Import the limiter instance
from ..page_classifier import PageClassifier  # Import classify_pages function
from ..pydantic_schemas import (
    AdjudicatedClaim,
    ExtractedData,
    ExtractedDataWithConfidence,
    InsuranceDetails,
    Token,
    User,
)
from ..rules_engine import adjudicate_claim
from ..value_extractor import extract_data_from_bill, llm_merge_extractions
import traceback  # add at top of file if not already imported


# import db
db = get_db()


# We use APIRouter to keep endpoint definitions organized
claims_router = APIRouter()


@claims_router.post("/extract")
@limiter.limit("10/minute")
async def create_extraction_request(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Receives a PDF medical bill, authenticates the user, applies rate limiting,
    identifies relevant pages, and concurrently calls the AI service per relevant page.
    Per-page intermediate files/JSON are NOT saved. The LLM-assisted merge is called
    to produce the final ExtractedDataWithConfidence. Any page extraction error aborts.
    """
    print(
        f"User '{current_user.username}' initiated an extraction for file: {file.filename}"
    )
    # Read the uploaded PDF file
    file_content = await file.read()

    pdf_reader = PdfReader(io.BytesIO(file_content))
    page_classifier = PageClassifier()
    # Classify pages to find relevant ones
    relevant_pages_bool = await page_classifier.classify_pages(file_content)
    print(f"Relevant pages identified: {relevant_pages_bool}")

    # Convert boolean list to page indices
    relevant_pages = [
        i for i, is_relevant in enumerate(relevant_pages_bool) if is_relevant
    ]
    print(f"Relevant page indices: {relevant_pages}")
    if not relevant_pages:
        raise HTTPException(status_code=400, detail="No relevant pages found in PDF.")

    # limit concurrency to max 50 as requested
    semaphore = asyncio.Semaphore(50)

    async def process_page(page_num: int):
        # create single-page PDF bytes (in-memory)
        writer = PdfWriter()
        writer.add_page(pdf_reader.pages[page_num])
        page_stream = io.BytesIO()
        writer.write(page_stream)
        page_bytes = page_stream.getvalue()

        # call extract_data_from_bill under semaphore
        async with semaphore:
            try:
                result = await extract_data_from_bill(page_bytes)
            except Exception as e:
                # bubble up to abort the whole operation
                raise

        return result

    # schedule concurrent extraction for relevant pages
    tasks = [asyncio.create_task(process_page(p)) for p in relevant_pages]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # abort if any task failed
    for r in results:
        if isinstance(r, Exception):
            # return error to caller
            raise HTTPException(status_code=500, detail=f"Page extraction failed: {r}")
    # Create a new PDF with only the relevant pages
    # all successful; results are ExtractedDataWithConfidence objects
    per_page_results = [r.dict() for r in results]

    # --- Sanitize per-page results ---
    # Ensure every 'confidence' field exists and is a float. If missing or None,
    # set to 0.0. This prevents Pydantic validation errors when merging.
    def _sanitize_confidences(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "confidence":
                    try:
                        # Treat None or non-convertible as 0.0
                        if v is None:
                            obj[k] = 0.0
                        else:
                            obj[k] = float(v)
                    except Exception:
                        obj[k] = 0.0
                else:
                    _sanitize_confidences(v)
        elif isinstance(obj, list):
            for e in obj:
                _sanitize_confidences(e)

    for p in per_page_results:
        _sanitize_confidences(p)

    # LLM-assisted merge (this helper should exist in value_extractor.py)
    merged = await llm_merge_extractions(per_page_results)

    # save the merged final result for auditing
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_dir = os.path.join("extraction_outputs", ts)
    os.makedirs(output_dir, exist_ok=True)
    merged_path = os.path.join(output_dir, "merged.json")
    try:
        with open(merged_path, "w", encoding="utf-8") as mf:
            json.dump(merged.dict(), mf, indent=2, default=str)
    except Exception:
        # non-fatal if save fails; merged will still be returned
        pass

    return merged


@claims_router.post("/adjudicate", response_model=AdjudicatedClaim)
@limiter.limit("10/minute")
async def create_adjudication_request(
    request: Request,
    extracted_data: ExtractedData,
    insurance_details: InsuranceDetails = Depends(InsuranceDetails),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),  # <-- Add DB session dependency
):
    """
    Receives structured bill data and applies the adjudication rules engine.
    This is the second step in the workflow.
    """
    adjudicated_result = await adjudicate_claim(extracted_data, insurance_details)
    print("saving the adjudicated claim to the database")
    db_claim = crud.create_claim_record(
        db=db,
        user=current_user,
        policy_id=insurance_details.policy_number,
        extracted_data=extracted_data,
        adjudicated_claim=adjudicated_result,
    )

    # --- Step 3: Add the DB-generated claim_id to our response ---
    # This ensures the API response includes the unique ID from the database
    # adjudicated_result.claim_id = db_claim.claim_id

    # print(f"Successfully saved claim with ID: {db_claim.claim_id}")
    return adjudicated_result


from uuid import UUID

from .. import pydantic_schemas as schemas


@claims_router.get("/{claim_id}", response_model=schemas.AdjudicatedClaim)
@limiter.limit("10/minute")
async def read_claim(
    request: Request,
    claim_id: UUID,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user),
):
    """
    Retrieves the full details of a single claim by its ID.
    """
    db_claim = crud.get_claim_by_id(db, claim_id=claim_id)
    if db_claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Security check: Ensure the user is requesting their own claim
    # In a real app, an admin might be allowed to bypass this
    if db_claim.submitted_by_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this claim")

    return db_claim.adjudicated_data


from typing import List


@claims_router.get("/")
@limiter.limit("10/minute")
async def read_claims(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user),
):
    """
    Retrieves a list of claims submitted by the current user.
    """
    claims = crud.get_claims_by_user(
        db, user_id=current_user.user_id, skip=skip, limit=limit
    )
    # return the full claim objects
    return claims
