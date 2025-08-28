
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
    print(f"User '{current_user.username}' initiated an extraction for file: {file.filename}")
    extracted_data = await extract_data_from_bill(file)
    return extracted_data


