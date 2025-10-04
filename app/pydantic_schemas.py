# app/pydantic_schemas.py

from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel, Field, conint

# Note: In a production financial system, using Decimal type is preferred
# for monetary values to avoid floating-point inaccuracies.
# For this version, we will use float for simplicity.


class LineItem(BaseModel):
    """
    Represents a single itemized line on the hospital bill.
    """

    description: str = Field(..., description="Description of the service or item.")
    quantity: float = Field(..., gt=0, description="Quantity of the item/service.")
    unit_price: float = Field(
        ..., ge=0, description="Price per unit of the item/service."
    )
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
    bill_no: Optional[str] = Field(
        None, description="The unique bill or invoice number."
    )
    bill_date: date = Field(..., description="Date the bill was issued.")
    admission_date: date = Field(..., description="Date of patient admission.")
    discharge_date: Optional[date] = Field(
        None, description="Date of patient discharge (if present)."
    )

    # Itemized Charges
    line_items: List[LineItem] = Field(..., description="List of all itemized charges.")

    # Total Amounts
    net_payable_amount: float = Field(
        ..., description="The final amount payable on the bill."
    )


class ClaimIntakeResponse(BaseModel):
    """
    The immediate response sent back to the user after submitting a claim.
    """

    claim_id: str = Field(
        ..., description="The unique ID assigned to this claim processing request."
    )
    status: str = Field(..., description="The initial status of the claim processing.")


class AdjudicatedLineItem(LineItem):
    """
    Represents a line item after adjudication rules have been applied.
    """

    status: str = Field(
        "Allowed", description="Status after adjudication (e.g., Allowed, Disallowed)."
    )
    allowed_amount: float = Field(
        ..., ge=0, description="The final amount allowed for this item."
    )
    disallowed_amount: float = Field(
        ..., ge=0, description="The amount disallowed for this item."
    )
    reason: Optional[str] = Field(
        None, description="Reason for any adjustment or denial."
    )


# --- NEW: Schema for the AI Auditor's response ---
class SanityCheckResult(BaseModel):
    """
    Defines the structure for the final AI sanity check review.
    """

    is_reasonable: bool = Field(
        ...,
        description="True if the overall claim adjudication "
        "seems logical and reasonable, False otherwise.",
    )
    reasoning: str = Field(
        ...,
        description="A brief, one-sentence explanation for the is_reasonable decision.",
    )
    flags: List[str] = Field(
        default_factory=list,
        description="A list of specific flags for any potential issues "
        " (e.g., 'Calculation Error', 'Logic Inconsistency', 'High Cost Anomaly', 'Missing Information', 'Policy Misinterpretation')."
    )


class AdjudicatedClaim(BaseModel):
    """
    The final response object containing the complete adjudication result.
    """

    hospital_name: str = Field(..., description="Name of the hospital.")
    patient_name: str = Field(..., description="Name of the patient.")
    bill_no: Optional[str] = Field(
        None, description="The unique bill or invoice number."
    )
    bill_date: date = Field(..., description="Date the bill was issued.")
    admission_date: date = Field(..., description="Date of patient admission.")
    discharge_date: Optional[date] = Field(
        None, description="Date of patient discharge (if present)."
    )

    adjudicated_line_items: List[AdjudicatedLineItem] = Field(
        ..., description="The list of line items after adjudication."
    )

    # Final Calculated Totals
    total_claimed_amount: float = Field(
        ..., description="The gross amount originally claimed."
    )
    total_amount_reimbursed: float = Field(
        ..., description="The total amount that can be reimbursed."
    )
    adjustments_log: list[str] = Field(
        ..., description="The adjustment made on the bill due to policy rules"
    )
    # --- ADD THIS NEW FIELD ---
    sanity_check_result: Optional[SanityCheckResult] = Field(
        None, description="The result from the final AI-powered sanity check."
    )

    class Config:
        from_attributes = True


# app/schemas.py


# (Keep all your existing models)
# ...


# --- NEW AUTHENTICATION MODELS ---
class Token(BaseModel):
    """
    Schema for returning an access token after user authentication.
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Data contained in the JWT token payload.
    """

    username: Optional[str] = None


class User(BaseModel):
    """
    Schema for returning a user from the API. Excludes the password.
    """

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    """
    Represents a user in the database, including hashed password.
    """

    hashed_password: str


# --- Reusable Models for Confidence Scoring ---
class FieldWithConfidence(BaseModel):
    """
    A generic field wrapper that includes the extracted value and the AI's confidence score.
    """

    value: Union[str, float, int, date, None] = Field(
        ..., description="The actual extracted value."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The AI's confidence in the accuracy of the value, from 0.0 to 1.0.",
    )


class LineItemWithConfidence(BaseModel):
    """
    Represents a single itemized line on the hospital bill with confidence scores."""

    description: FieldWithConfidence
    quantity: FieldWithConfidence
    unit_price: FieldWithConfidence
    total_amount: FieldWithConfidence


class ExtractedDataWithConfidence(BaseModel):
    """
    Represents the structured data extracted from a medical bill by the AI model,
    with confidence scores for each field.
    """

    hospital_name: FieldWithConfidence
    patient_name: FieldWithConfidence
    bill_date: FieldWithConfidence
    bill_no: FieldWithConfidence
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
        description="The name of the best matching sub-limit rules, or null if none apply.",
    )


class UserUpdateAdmin(BaseModel):
    """Schema for updating a user's details from the admin panel."""

    full_name: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # Admin can reset a password


class UserBase(BaseModel):
    "class representing the base user schema."

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """
    Schema for creating a new user. Includes the password.
    """

    password: str
    role_id: conint(ge=1, le=2) = Field(
        ..., description="Role ID: 1 for admin, 2 for regular user."
    )


# You can also update your existing User schema to inherit from UserBase
# for consistency, though it's not required to fix the error.
# class User(UserBase):
#     """
#     Schema for returning a user from the API. Excludes the password.
#     """

#     user_id: int
#     is_active: bool
#     role_id: int

#     class Config:
#         from_attributes = True  # Allows creating Pydantic model from ORM model


class Policy(BaseModel):
    """
    Schema for representing a policy rulebook.
    """

    policy_id: str
    policy_name: str
    rules: dict  # The entire rules JSON object

    class Config:
        from_attributes = True  # Allows creating Pydantic model from ORM model


