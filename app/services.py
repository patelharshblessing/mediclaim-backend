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

# async def extract_data_from_bill(file: UploadFile) -> ExtractedData:
#     """
#     Orchestrates the file validation and AI data extraction.
#     For now, it returns a hardcoded mock response.
#     """
#     validate_and_preprocess_file(file)
    
#     # In a real scenario, we would send the preprocessed file/image
#     # to the Claude 3.5 Sonnet API here.
    
#     print("Simulating AI extraction...")
    
#     # --- MOCK RESPONSE ---
#     # This hardcoded data simulates what the AI would return.
#     mock_data = ExtractedData(
#         hospital_name="Kanpur General Hospital",
#         patient_name="R. Sharma",
#         policy_number="POL-123456789",
#         insurance_provider="ABC Health Insurance",
#         bill_no="B-12345",
#         bill_date=datetime.date(2025, 8, 10),
#         admission_date=datetime.date(2025, 8, 1),
#         discharge_date=datetime.date(2025, 8, 10),
#         line_items=[
#             LineItem(description="Room Rent - Semi Private", quantity=9.0, unit_price=4000.0, total_amount=36000.0),
#             LineItem(description="Doctor Consultation", quantity=10.0, unit_price=1000.0, total_amount=10000.0),
#             LineItem(description="CBC Test", quantity=2.0, unit_price=400.0, total_amount=800.0), # Diagnostic
#             LineItem(description="CT Scan - Brain", quantity=1.0, unit_price=3500.0, total_amount=3500.0), # Diagnostic
#             LineItem(description="Operation Theatre Charges", quantity=1.0, unit_price=15000.0, total_amount=15000.0), # Procedure
#             LineItem(description="Anesthesia Charges", quantity=1.0, unit_price=7500.0, total_amount=7500.0), # Procedure
#             LineItem(description="Nursing Charges", quantity=9.0, unit_price=500.0, total_amount=4500.0), # Professional Fees
#             LineItem(description="Dolo 650mg", quantity=20.0, unit_price=2.5, total_amount=50.0), # Pharmacy
#             LineItem(description="Syringe", quantity=10.0, unit_price=10.0, total_amount=100.0), # Non-payable item
#             LineItem(description="Sterile Gloves", quantity=15.0, unit_price=50.0, total_amount=750.0), # Non-payable item
#             LineItem(description="IV Drip Set", quantity=10.0, unit_price=150.0, total_amount=1500.0), # Non-payable item
#             LineItem(description="Band-Aid", quantity=5.0, unit_price=10.0, total_amount=50.0) # Non-payable item
#         ],
#         gross_amount=46800.0,
#         discount_or_concession=0.0,
#         net_payable_amount=46800.0
#     )
#     return mock_data

from .pydantic_schemas import AdjudicatedClaim
from .pydantic_schemas import AdjudicatedLineItem


def adjudicate_claim(extracted_data: ExtractedData) -> AdjudicatedClaim:
    """
    Applies adjudication rules to the extracted data.
    For now, it returns a hardcoded mock response.
    """
    print("Simulating adjudication process...")
    
    # --- MOCK RESPONSE ---
    # This hardcoded data simulates what the adjudication engine would return.
    mock_adjudicated_claim = AdjudicatedClaim(
        hospital_name="Kanpur General Hospital",
        patient_name="R. Sharma",
        policy_number="POL-123456789",
        insurance_provider="ABC Health Insurance",
        bill_no="B-12345",
        bill_date=datetime.date(2025, 8, 10),
        admission_date=datetime.date(2025, 8, 1),
        discharge_date=datetime.date(2025, 8, 10),
        adjudicated_line_items=[
            AdjudicatedLineItem(description="Room Rent - Semi Private", quantity=9.0, unit_price=4000.0, total_amount=36000.0, status="Allowed", allowed_amount=36000.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Doctor Consultation", quantity=10.0, unit_price=1000.0, total_amount=10000.0, status="Allowed", allowed_amount=10000.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="CBC Test", quantity=2.0, unit_price=400.0, total_amount=800.0, status="Allowed", allowed_amount=800.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="CT Scan - Brain", quantity=1.0, unit_price=3500.0, total_amount=3500.0, status="Allowed", allowed_amount=3500.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Operation Theatre Charges", quantity=1.0, unit_price=15000.0, total_amount=15000.0, status="Allowed", allowed_amount=15000.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Anesthesia Charges", quantity=1.0, unit_price=7500.0, total_amount=7500.0, status="Allowed", allowed_amount=7500.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Nursing Charges", quantity=9.0, unit_price=500.0, total_amount=4500.0, status="Allowed", allowed_amount=4500.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Dolo 650mg", quantity=20.0, unit_price=2.5, total_amount=50.0, status="Allowed", allowed_amount=50.0, disallowed_amount=0.0),
            AdjudicatedLineItem(description="Syringe", quantity=10.0, unit_price=10.0, total_amount=100.0, status="Disallowed", allowed_amount=0.0, disallowed_amount=100.0, reason="As per IRDAI guidelines, standard consumables like syringes are non-payable."),
            AdjudicatedLineItem(description="Sterile Gloves", quantity=15.0, unit_price=50.0, total_amount=750.0, status="Disallowed", allowed_amount=0.0, disallowed_amount=750.0, reason="As per IRDAI guidelines, standard consumables like gloves are non-payable."),
            AdjudicatedLineItem(description="IV Drip Set", quantity=10.0, unit_price=150.0, total_amount=1500.0, status="Disallowed", allowed_amount=0.0, disallowed_amount=1500.0, reason="As per IRDAI guidelines, standard consumables like IV sets are non-payable."),
            AdjudicatedLineItem(description="Band-Aid", quantity=5.0, unit_price=10.0, total_amount=50.0, status="Disallowed", allowed_amount=0.0, disallowed_amount=50.0, reason="As per IRDAI guidelines, standard consumables like band-aids are non-payable.")
        ],
        total_claimed_amount=46800.0,
        total_allowed_amount=46050.0,
    )
    
    return mock_adjudicated_claim


