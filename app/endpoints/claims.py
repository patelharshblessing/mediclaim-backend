# app/endpoints.py

from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse
from ..pydantic_schemas import ExtractedData
# from ..value_extractor import extract_data_from_bill
from ..value_extraction_gemini import extract_data_from_bill
from ..pydantic_schemas import ExtractedDataWithConfidence
from ..pydantic_schemas import AdjudicatedClaim
from ..rules_engine import adjudicate_claim
from ..limiter import limiter # Import the limiter instance
from ..pydantic_schemas import InsuranceDetails
from ..pydantic_schemas import Token
from fastapi.security import OAuth2PasswordRequestForm
from .. import auth
from datetime import timedelta
from ..config import settings
from fastapi import status
from slowapi.errors import RateLimitExceeded
from fastapi import HTTPException
from ..pydantic_schemas import User
from ..database import get_db
from sqlalchemy.orm import Session
from .. import crud
# import db
db=get_db()


# We use APIRouter to keep endpoint definitions organized
claims_router = APIRouter()


@claims_router.post("/extract", response_model=ExtractedDataWithConfidence)
@limiter.limit("10/minute") 
async def create_extraction_request(
    request: Request, 
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Receives a PDF medical bill, authenticates the user, applies rate limiting,
    and calls the AI service to extract structured data.
    """
    print(f"User '{current_user.username}' initiated an extraction for file: {file.filename}")
    
    # Call the core logic from your value_extractor service
    extracted_data = await extract_data_from_bill(file)
    
    return extracted_data

@claims_router.post("/adjudicate", response_model=AdjudicatedClaim)
@limiter.limit("10/minute")
async def create_adjudication_request(
    request: Request,
    extracted_data: ExtractedData,
    insurance_details: InsuranceDetails = Depends(InsuranceDetails),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)  # <-- Add DB session dependency
):
    """
    Receives structured bill data and applies the adjudication rules engine.
    This is the second step in the workflow.
    """
    adjudicated_result =  await adjudicate_claim(extracted_data, insurance_details)
    print("saving the adjudicated claim to the database")
    db_claim = crud.create_claim_record(
        db=db,
        user=current_user,
        policy_id=insurance_details.policy_number,
        extracted_data=extracted_data,
        adjudicated_claim=adjudicated_result
    )
    
    # --- Step 3: Add the DB-generated claim_id to our response ---
    # This ensures the API response includes the unique ID from the database
    # adjudicated_result.claim_id = db_claim.claim_id
    
    # print(f"Successfully saved claim with ID: {db_claim.claim_id}")
    return adjudicated_result





from .. import pydantic_schemas as schemas
from uuid import UUID

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
    claims = crud.get_claims_by_user(db, user_id=current_user.user_id, skip=skip, limit=limit)
    # return the full claim objects
    return claims



