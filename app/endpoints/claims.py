# app/endpoint/claims.py

import io  # For in-memory file handling
import time
from datetime import timedelta

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
from ..normalization_service import NormalizationService
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
from ..value_extractor import extract_data_from_bill

# import db
db = get_db()

LOG_FILE = "time_logging.txt"


def log_time(step: str, value: any):
    with open(LOG_FILE, "a") as log_file:
        if isinstance(value, float):
            log_file.write(f"{step}: {value:.2f} seconds\n")
        else:
            log_file.write(f"{step}: {value}\n")


# We use APIRouter to keep endpoint definitions organized
claims_router = APIRouter()


@claims_router.post("/extract", response_model=ExtractedDataWithConfidence)
@limiter.limit("10/minute")
async def create_extraction_request(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Receives a PDF medical bill, authenticates the user, applies rate limiting,
    identifies relevant pages, and calls the AI service to extract structured data.
    """
    print(
        f"User '{current_user.username}' initiated an extraction for file: {file.filename}"
    )

    # Read the uploaded PDF file
    log_time("File Name", file.filename if file.filename else "Unknown")
    file_content = await file.read()

    # pdf_reader = PdfReader(io.BytesIO(file_content))
    # total_pages = len(pdf_reader.pages)

    # page_classifier = PageClassifier()
    # # Classify pages to find relevant ones
    # start_time = time.time()
    # relevant_pages_bool = await page_classifier.classify_pages(file_content)
    # duration = time.time() - start_time
    
    # log_time("Page Classification", duration)

    # relevant_pages = [
    #     i for i, is_relevant in enumerate(relevant_pages_bool) if is_relevant
    # ]

    # # Log additional details
    
    # log_time("Total Pages", total_pages)
    # log_time("Relevant Pages", len(relevant_pages))

    # print(f"Relevant pages identified: {relevant_pages_bool}")
    # print(f"Relevant page indices: {relevant_pages}")
    # # Create a new PDF with only the relevant pages
    # relevant_pdf_writer = PdfWriter()
    # for page_num in relevant_pages:
    #     relevant_pdf_writer.add_page(pdf_reader.pages[page_num])

    # # Write the relevant pages to an in-memory file
    # relevant_pdf_stream = io.BytesIO()
    # relevant_pdf_writer.write(relevant_pdf_stream)
    # relevant_pdf_stream.seek(0)
    # # Save the relevant pages as a PDF file for cross-checking
    # with open("relevant_pages.pdf", "wb") as f:
    #     f.write(relevant_pdf_stream.getvalue())
    # print("Relevant pages saved as 'relevant_pages.pdf'")

    # # Call the core logic from your value_extractor service with the relevant pages
    # start_time = time.time()
    # extracted_data = await extract_data_from_bill(relevant_pdf_stream.getvalue())
    extracted_data = await extract_data_from_bill(file_content)
    # log_time("Values Extraction", time.time() - start_time)

    return extracted_data


normalizationservice = NormalizationService()


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
    start_time = time.time()
    adjudicated_result = await adjudicate_claim(
        extracted_data, insurance_details, normalizationservice=normalizationservice
    )
    log_time("Total adjudication time", time.time() - start_time)

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
