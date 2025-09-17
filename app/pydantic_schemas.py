# app/schemas.py

from datetime import date
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, conint

# Note: In a production financial system, using Decimal type is preferred
# for monetary values to avoid floating-point inaccuracies.
# For this version, we will use float for simplicity.


class LineItem(BaseModel):
    """
    Represents a single itemized line on the hospital bill.
    """

    description: str = Field(..., description="Description of the service or item.")
    quantity: float = Field(..., gt=0, description="Quantity of the item/service.")
    unit_price: float = Field(..., description="Price per unit of the item/service.")
    total_amount: float = Field(..., description="Total cost for this line item.")


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
    The 'status' is now automatically computed based on the amounts.
    """

    # Note: The original 'status' field has been removed.

    allowed_amount: float = Field(
        ..., description="The final amount allowed for this item."
    )
    disallowed_amount: float = Field(
        ..., description="The amount disallowed for this item."
    )
    reason: Optional[str] = Field(
        None, description="Reason for any adjustment or denial."
    )

    @computed_field
    @property
    def status(self) -> str:
        """
        Computes the status based on the allowed and disallowed amounts.
        """
        total = self.allowed_amount + self.disallowed_amount

        if total == 0:
            return "Allowed"
        elif self.allowed_amount > 0 and self.disallowed_amount > 0:
            return "Partially Allowed"
        elif self.allowed_amount > 0 and self.disallowed_amount == 0:
            return "Allowed"
        else:  # Covers the case where allowed_amount is 0
            return "Disallowed"


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
        description="A list of specific flags for any potential issues"
        " (e.g., 'High Pharmacy Cost').",
    )


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


# --- NEW: Response model for the /extract endpoint ---
class ExtractionResponse(BaseModel):
    """
    The response sent back after a successful extraction, containing the
    claim_id needed for the next step.
    """

    claim_id: UUID
    extracted_data: ExtractedDataWithConfidence


# --- NEW: Request body model for the /adjudicate endpoint ---
class AdjudicationRequest(BaseModel):
    """
    The request body for the adjudication endpoint, containing the
    human-verified extracted data and the policy details.
    """

    extracted_data: ExtractedData
    insurance_details: InsuranceDetails


# --- NEW: Schema for the Performance Report ---
class PerformanceReport(BaseModel):
    """Holds all the timing and count metrics for a claim's lifecycle."""

    # Extraction Metrics
    num_pages: Optional[int] = None
    extract_processing_time_sec: Optional[float] = None
    extract_cost_usd: Optional[float] = None  # Placeholder for future use

    # Adjudication Metrics
    total_items_processed: Optional[int] = None
    rules_applied_count: Optional[int] = None
    adjudicate_processing_time_sec: Optional[float] = None
    time_irda_filter_sec: Optional[float] = None
    time_rule_matching_sec: Optional[float] = None
    time_rule_application_sec: Optional[float] = None
    time_sanity_check_sec: Optional[float] = None
    cost_rule_matching_usd: Optional[float] = None  # Placeholder for future use
    cost_rule_application_usd: Optional[float] = None  # Placeholder for future use
    cost_sanity_check_usd: Optional[float] = None  # Placeholder for future use

    class Config:
        from_attributes = True


class AdjudicatedClaim(BaseModel):
    """
    The final response object containing the complete adjudication result.
    """

    # claim_id: UUID
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
    total_allowed_amount: float = Field(
        ..., description="The total amount allowed after adjudication."
    )
    adjustments_log: list[str] = Field(
        ..., description="The adjustment made on the bill due to policy rules"
    )
    # --- ADD THIS NEW FIELD ---
    sanity_check_result: Optional[SanityCheckResult] = Field(
        None, description="The result from the final AI-powered sanity check."
    )
    performance_report: Optional[PerformanceReport] = None

    class Config:
        from_attributes = True
