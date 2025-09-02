# app/services.py

import datetime
from fastapi import UploadFile, HTTPException, status
from .pydantic_schemas import ExtractedData, LineItem
from .config import settings

def validate_and_preprocess_file(file: UploadFile) -> bool:
    """
    Performs validation checks on the uploaded file.
    """
    # Check file size
    size_in_mb = file.size / (1024 * 1024)
    if size_in_mb > settings.FILE_SIZE_LIMIT_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {settings.FILE_SIZE_LIMIT_MB}MB."
        )

    # Check file type (MIME type)
    if file.content_type not in settings.ALLOWED_MIMETYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Please upload a PDF."
        )
    
    # Placeholder for PDF to image conversion
    print("File validated successfully. Pretending to convert PDF to image...")
    return True
