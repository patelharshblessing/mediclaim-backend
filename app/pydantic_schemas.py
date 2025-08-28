# app/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import date

# Note: In a production financial system, using Decimal type is preferred
# for monetary values to avoid floating-point inaccuracies.
# For this version, we will use float for simplicity.


class LineItem(BaseModel):
    """
    Represents a single itemized line on the hospital bill.
    """
    description: str = Field(..., description="Description of the service or item.")
    quantity: float = Field(..., gt=0, description="Quantity of the item/service.")
    unit_price: float = Field(..., ge=0, description="Price per unit of the item/service.")
    total_amount: float = Field(..., ge=0, description="Total cost for this line item.")


class InsuranceDetails(BaseModel):
    """
    Represents the insurance details associated with the claim.
    """
    policy_number: str = Field(..., description="Insurance policy number.")
    insurance_provider: str = Field(..., description="Name of the insurance provider.")


class ExtractedData(BaseModel):
    """
    Represents the structured data extracted from a medical bill by the AI model.
    """
    # Header Information
    hospital_name: str = Field(..., description="Name of the hospital.")
    patient_name: str = Field(..., description="Name of the patient.")
    bill_no: Optional[str] = Field(None, description="The unique bill or invoice number.")
    bill_date: date = Field(..., description="Date the bill was issued.")
    admission_date: date = Field(..., description="Date of patient admission.")
    discharge_date: Optional[date] = Field(None, description="Date of patient discharge (if present).")
   
    # Itemized Charges
    line_items: List[LineItem] = Field(..., description="List of all itemized charges.")

    # Total Amounts
    net_payable_amount: float = Field(..., description="The final amount payable on the bill.")


class ClaimIntakeResponse(BaseModel):
    """
    The immediate response sent back to the user after submitting a claim.
    """
    claim_id: str = Field(..., description="The unique ID assigned to this claim processing request.")
    status: str = Field(..., description="The initial status of the claim processing.")



class AdjudicatedLineItem(LineItem):
    """
    Represents a line item after adjudication rules have been applied.
    """
    status: str = Field("Allowed", description="Status after adjudication (e.g., Allowed, Disallowed).")
    allowed_amount: float = Field(..., ge=0, description="The final amount allowed for this item.")
    disallowed_amount: float = Field(..., ge=0, description="The amount disallowed for this item.")
    reason: Optional[str] = Field(None, description="Reason for any adjustment or denial.")


class AdjudicatedClaim(BaseModel):
    """
    The final response object containing the complete adjudication result.
    """
    hospital_name: str = Field(..., description="Name of the hospital.")
    patient_name: str = Field(..., description="Name of the patient.")
    bill_no: Optional[str] = Field(None, description="The unique bill or invoice number.")
    bill_date: date = Field(..., description="Date the bill was issued.")
    admission_date: date = Field(..., description="Date of patient admission.")
    discharge_date: Optional[date] = Field(None, description="Date of patient discharge (if present).")

    adjudicated_line_items: List[AdjudicatedLineItem] = Field(..., description="The list of line items after adjudication.")
    
    # Final Calculated Totals
    total_claimed_amount: float = Field(..., description="The gross amount originally claimed.")
    total_allowed_amount: float = Field(..., description="The total amount allowed after adjudication.")
    adjustments_log : list[str] = Field(...,description="The adjustment made on the bill due to policy rules")
# app/schemas.py

# (Keep all your existing models)
# ...

# --- NEW AUTHENTICATION MODELS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str





# --- Reusable Models for Confidence Scoring ---
class FieldWithConfidence(BaseModel):
    value: Union[str, float, int, date, None] = Field(..., description="The actual extracted value.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="The AI's confidence in the accuracy of the value, from 0.0 to 1.0.")

class LineItemWithConfidence(BaseModel):
    description: FieldWithConfidence
    quantity: FieldWithConfidence
    unit_price: FieldWithConfidence
    total_amount: FieldWithConfidence

class ExtractedDataWithConfidence(BaseModel):
    hospital_name: FieldWithConfidence
    patient_name: FieldWithConfidence
    bill_date: FieldWithConfidence
    admission_date: FieldWithConfidence
    discharge_date: FieldWithConfidence
    net_payable_amount: FieldWithConfidence
    line_items: List[LineItemWithConfidence]

class PolicyRuleMatch(BaseModel):
    """
    Defines the expected JSON structure from the LLM for rule matching.
    """
    applicable_rule_name: Optional[str] = Field(
        None,
        description="The name of the best matching sub-limit rules, or null if none apply."
    )