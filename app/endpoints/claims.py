# app/endpoints.py

import time
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from .. import auth, crud
from ..config import settings
from ..database import get_db
from ..limiter import limiter  # Import the limiter instance
from ..normalization_service import NormalizationService
from ..pydantic_schemas import (
    AdjudicatedClaim,
    AdjudicationRequest,
    ExtractedData,
    ExtractedDataWithConfidence,
    ExtractionResponse,
    InsuranceDetails,
    PerformanceReport,
    Token,
    User,
)
from ..rules_engine import adjudicate_claim

# from ..value_extractor import extract_data_from_bill
from ..value_extractor import extract_data_from_bill

# import db
db = get_db()


# We use APIRouter to keep endpoint definitions organized
claims_router = APIRouter()

from pdf2image import convert_from_bytes


def count_pdf_pages(file_content: bytes) -> int:
    """Helper function to count pages in a PDF."""
    try:
        images = convert_from_bytes(file_content)
        return len(images)
    except Exception:
        # If pdf2image fails, return a default/error value
        return 0


@claims_router.post("/extract", response_model=ExtractionResponse)
@limiter.limit("10/minute")
async def create_extraction_request(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Receives a PDF medical bill, authenticates the user, applies rate limiting,
    and calls the AI service to extract structured data.
    """
    start_time = time.monotonic()
    file_content = await file.read()
    print(
        f"User '{current_user.username}' initiated an extraction for file: {file.filename}"
    )

    # Call the core logic from your value_extractor service
    extracted_data = await extract_data_from_bill(file_content)
    num_pages = count_pdf_pages(file_content)
    processing_time = time.monotonic() - start_time

    # --- 2. Create Initial Claim and Log in DB ---
    db_claim = crud.create_claim_with_log(
        db=db,
        user_id=current_user.user_id,
        filename=file.filename,
        num_pages=num_pages,
        extract_time=processing_time,
    )
    if not db_claim:
        raise HTTPException(
            status_code=500, detail="Failed to create a new claim record."
        )

    # --- 3. Return the claim_id and extracted data for human review ---
    return ExtractionResponse(
        claim_id=db_claim.claim_id,
        extracted_data=ExtractedDataWithConfidence(**extracted_data.dict()),
    )


@claims_router.post("/adjudicate/{claim_id}", response_model=AdjudicatedClaim)
@limiter.limit("10/minute")
async def create_adjudication_request(
    request: Request,
    claim_id: UUID,
    adjudication_req: AdjudicationRequest,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),  # <-- Add DB session dependency
):
    """
    Receives structured bill data and applies the adjudication rules engine.
    This is the second step in the workflow.
    """
    normalizationservice = NormalizationService()
    # --- 1. Run the Adjudication Rules Engine ---
    adjudicated_result, perf_metrics = await adjudicate_claim(
        extracted_data=adjudication_req.extracted_data,
        insurance_details=adjudication_req.insurance_details,
        normalizationservice=normalizationservice,
    )

    # --- 2. Update the Claim and Log in DB ---
    db_claim = crud.update_claim_after_adjudication(
        db=db,
        claim_id=claim_id,
        policy_id=adjudication_req.insurance_details.policy_number,
        extracted_data=adjudication_req.extracted_data,
        adjudicated_data=adjudicated_result,
        perf_metrics=perf_metrics,
    )

    if not db_claim:
        raise HTTPException(
            status_code=404, detail=f"Claim with ID {claim_id} not found."
        )

    # --- 3. Prepare and return the final response ---
    # Populate the performance report from the database log
    perf_report = PerformanceReport.from_orm(db_claim.performance_log)
    adjudicated_result.performance_report = perf_report
    # adjudicated_result.claim_id = db_claim.claim_id
    print(adjudicated_result.performance_report)
    return adjudicated_result


from typing import List
from uuid import UUID

from .. import pydantic_schemas as schemas


@claims_router.get("/{claim_id}",)
@limiter.limit("10/minute")
async def read_claim(
    request: Request,
    claim_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Retrieves the full details of a single claim by its ID.
    """
    db_claim = crud.get_claim_by_id(db, claim_id=claim_id)
    if db_claim is None or db_claim.adjudicated_data is None:
        raise HTTPException(
            status_code=404, detail="Claim not found or not adjudicated."
        )

    if db_claim.submitted_by_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this claim")
    return db_claim

    # # Parse the stored JSON back into the Pydantic model
    # adjudicated_claim_data = AdjudicatedClaim.model_validate(db_claim.adjudicated_data)

    # # Populate the performance report from the log
    # if db_claim.performance_log:
    #     perf_report = PerformanceReport.from_orm(db_claim.performance_log)
    #     adjudicated_claim_data.performance_report = perf_report

    # adjudicated_claim_data.claim_id = db_claim.claim_id

    # return adjudicated_claim_data


@claims_router.get("/")
@limiter.limit("10/minute")
async def read_claims(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    """
    Retrieves a list of adjudicated claims submitted by the current user.
    """
    db_claims = crud.get_claims_by_user(
        db, user_id=current_user.user_id, skip=skip, limit=limit
    )

    # response_claims = []
    # for claim in db_claims:
    #     if claim.adjudicated_data:  # Only include adjudicated claims
    #         claim_data = AdjudicatedClaim.model_validate(claim.adjudicated_data)
    #         # claim_data.claim_id = claim.claim_id
    #         if claim.performance_log:
    #             claim_data.performance_report = PerformanceReport.from_orm(
    #                 claim.performance_log
    #             )
    #         response_claims.append(claim_data.model_dump())

    return db_claims
