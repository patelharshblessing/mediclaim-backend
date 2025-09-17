# app/models.py
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, unique=True, index=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role")
    claims = relationship("Claim", back_populates="submitter")


class Policy(Base):
    __tablename__ = "policies"
    policy_id = Column(String, primary_key=True, index=True)
    policy_name = Column(String, nullable=False)
    rules = Column(JSONB, nullable=False)  # Stores the entire policy rulebook JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())






class Claim(Base):
    """Represents a claim submitted by a user."""
    __tablename__ = "claims"
    claim_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by_user_id = Column(Integer, ForeignKey("users.user_id"))
    # --- UPDATE: policy_id is now nullable ---
    # It will be NULL until the adjudication step.
    policy_id = Column(String, ForeignKey("policies.policy_id"), nullable=True)
    status = Column(String, default="processing")
    original_pdf_filename = Column(String)
    extracted_data = Column(JSONB, nullable=True)
    adjudicated_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submitter = relationship("User", back_populates="claims")
    policy = relationship("Policy")
    # Add a one-to-one relationship to the new performance log table
    performance_log = relationship(
        "PerformanceLog",
        back_populates="claim",
        uselist=False,
        cascade="all, delete-orphan",
    )


# --- NEW: Unified Table for Performance Logs ---
class PerformanceLog(Base):
    __tablename__ = "performance_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(
        UUID(as_uuid=True), ForeignKey("claims.claim_id"), unique=True, nullable=False
    )

    # --- Extraction Metrics ---
    num_pages = Column(Integer)
    extract_processing_time_sec = Column(Float)
    extract_cost_usd = Column(Float, nullable=True)  # Placeholder for future use

    # --- Adjudication Metrics ---
    total_items_processed = Column(Integer, nullable=True)
    rules_applied_count = Column(Integer, nullable=True)
    adjudicate_processing_time_sec = Column(Float, nullable=True)
    time_irda_filter_sec = Column(Float, nullable=True)
    time_rule_matching_sec = Column(Float, nullable=True)
    time_rule_application_sec = Column(Float, nullable=True)
    time_sanity_check_sec = Column(Float, nullable=True)
    cost_rule_matching_usd = Column(Float, nullable=True)  # Placeholders for future use
    cost_rule_application_usd = Column(Float, nullable=True)
    cost_sanity_check_usd = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="performance_log")



