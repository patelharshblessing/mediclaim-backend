# app/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime,
    func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

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

class Policy(Base):
    __tablename__ = "policies"
    policy_id = Column(String, primary_key=True, index=True)
    policy_name = Column(String, nullable=False)
    rules = Column(JSONB, nullable=False) # Stores the entire policy rulebook JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Claim(Base):
    __tablename__ = "claims"
    claim_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by_user_id = Column(Integer, ForeignKey("users.user_id"))
    policy_id = Column(String, ForeignKey("policies.policy_id"))
    status = Column(String, default="processing")
    original_pdf_filename = Column(String)
    extracted_data = Column(JSONB) # Stores the JSON from the /extract API
    adjudicated_data = Column(JSONB) # Stores the final AdjudicatedClaim object
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    submitter = relationship("User")
    policy = relationship("Policy")