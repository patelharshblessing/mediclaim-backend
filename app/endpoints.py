# app/endpoints.py

from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse
from .pydantic_schemas import ExtractedData
from .value_extractor import extract_data_from_bill
from .pydantic_schemas import ExtractedDataWithConfidence
from .pydantic_schemas import AdjudicatedClaim
from .rules_engine import adjudicate_claim
from .limiter import limiter # Import the limiter instance
from .pydantic_schemas import InsuranceDetails
from .pydantic_schemas import Token
from fastapi.security import OAuth2PasswordRequestForm
from . import auth
from datetime import timedelta
from .config import settings
from fastapi import status
from slowapi.errors import RateLimitExceeded
from fastapi import HTTPException
from .pydantic_schemas import User



# We use APIRouter to keep endpoint definitions organized
router = APIRouter()



@router.post("/extract", response_model=ExtractedDataWithConfidence)
@limiter.limit("10/minute") 
async def create_extraction_request(
    request: Request, 
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user)
    ):
    """
    Receives a PDF medical bill, validates it, and calls the AI
    service to extract structured data.
    """
    extracted_data = await extract_data_from_bill(file)
    return extracted_data



@router.post("/adjudicate", response_model=AdjudicatedClaim)
@limiter.limit("30/minute")
async def create_adjudication_request(
    request: Request,
    extracted_data: ExtractedData,
    insurance_details: InsuranceDetails = Depends(InsuranceDetails),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Receives structured bill data and applies the adjudication rules engine.
    This is the second step in the workflow.
    """
    adjudicated_result =  await adjudicate_claim(extracted_data, insurance_details)
    return adjudicated_result



@router.post("/token", response_model=Token)
@limiter.limit("30/minute")
async def login_for_access_token(request: Request,form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.get_user(auth.fake_users_db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
