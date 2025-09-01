# app/crud.py

from sqlalchemy.orm import Session
from . import pydantic_schemas as schemas
from . import   database_schema as models
from uuid import UUID
from . import auth
def create_claim_record(
    db: Session, 
    user: schemas.User, 
    policy_id: str,
    extracted_data: schemas.ExtractedData, 
    adjudicated_claim: schemas.AdjudicatedClaim
) -> models.Claim:
    """
    Creates a new claim record in the database.
    """
    # Create a new SQLAlchemy Claim model instance
    db_claim = models.Claim(
        submitted_by_user_id=user.user_id,
        policy_id=policy_id,
        status="completed", # Mark the status as completed
        # Convert Pydantic models to dictionaries for storing in JSONB fields
        extracted_data=extracted_data.model_dump(mode='json'),
        adjudicated_data=adjudicated_claim.model_dump(mode='json')
    )
    
    # Add the new record to the session, commit it to the database,
    # and refresh the instance to get the new claim_id
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    
    return db_claim

def get_claim_by_id(db: Session, claim_id: UUID) -> models.Claim | None:
    """
    Fetches a single claim from the database by its UUID.
    """
    return db.query(models.Claim).filter(models.Claim.claim_id == claim_id).first()

def get_claims_by_user(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> list[models.Claim]:
    """
    Fetches a paginated list of claims submitted by a specific user.
    """
    return (
        db.query(models.Claim)
        .filter(models.Claim.submitted_by_user_id == user_id)
        .order_by(models.Claim.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )



def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

# import joinedload
from sqlalchemy.orm import joinedload
def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Fetches a paginated list of all users."""
    
    # --- FIX: Add .options(joinedload(...)) to eagerly load the role ---
    return (
        db.query(models.User)
        .options(joinedload(models.User.role)) # This tells SQLAlchemy to fetch the role too
        .order_by(models.User.user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role_id=user.role_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # --- FIX: After creating, re-fetch the user with the role loaded ---
    return (
        db.query(models.User)
        .options(joinedload(models.User.role))
        .filter(models.User.user_id == db_user.user_id)
        .first()
    )

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdateAdmin):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = auth.get_password_hash(update_data["password"])
        del update_data["password"]
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    
    # --- FIX: After updating, re-fetch the user with the role loaded ---
    return (
        db.query(models.User)
        .options(joinedload(models.User.role))
        .filter(models.User.user_id == db_user.user_id)
        .first()
    )

def get_policies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Policy).offset(skip).limit(limit).all()

def get_policy_by_id(db: Session, policy_id: str):
    return db.query(models.Policy).filter(models.Policy.policy_id == policy_id).first()

def update_policy(db: Session, policy_id: str, policy_update: schemas.Policy):
    db_policy = get_policy_by_id(db, policy_id)
    if not db_policy:
        return None
    db_policy.policy_name = policy_update.policy_name
    db_policy.rules = policy_update.rules
    db.commit()
    db.refresh(db_policy)
    return db_policy

def get_user(db: Session, username: str):
    """
    Fetches a single user from the database by their username.
    """
    return (
        db.query(models.User)
        .options(joinedload(models.User.role))
        .filter(models.User.username == username)
        .first()
    )

