# app/endpoints/admin.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status,Query
from sqlalchemy.orm import Session

from .. import auth, crud, pydantic_schemas
from ..database import get_db
from ..limiter import limiter

admin_router = APIRouter()


# --- User Management Endpoints ---
@admin_router.post(
    "/users", response_model=pydantic_schemas.User, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
def create_new_user(
    request: Request,
    user: pydantic_schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    db_user = crud.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    return crud.create_user(db=db, user=user)


@admin_router.get("/users", response_model=List[pydantic_schemas.User])
@limiter.limit("10/minute")
def read_all_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@admin_router.put("/users/{user_id}", response_model=pydantic_schemas.User)
@limiter.limit("10/minute")
def update_existing_user(
    request: Request,
    user_id: int,
    user_update: pydantic_schemas.UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# --- Policy Management Endpoints ---


@admin_router.get("/policies", response_model=List[pydantic_schemas.Policy])
@limiter.limit("10/minute")
def read_all_policies(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    policies = crud.get_policies(db, skip=skip, limit=limit)
    return policies


@admin_router.get("/policies/{policy_id}", response_model=pydantic_schemas.Policy)
@limiter.limit("10/minute")
def read_specific_policy(
    request: Request,
    policy_id: str,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    db_policy = crud.get_policy_by_id(db, policy_id=policy_id)
    if db_policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db_policy


@admin_router.put("/policies/{policy_id}", response_model=pydantic_schemas.Policy)
@limiter.limit("10/minute")
def update_existing_policy(
    request: Request,
    policy_id: str,
    policy_update: pydantic_schemas.Policy,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    db_policy = crud.update_policy(db, policy_id=policy_id, policy_update=policy_update)
    if db_policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db_policy


from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm

from ..config import settings
from ..pydantic_schemas import Token

token_router = APIRouter()


# Login for access token check from the database
@token_router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db),  # <-- Add DB session dependency
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # Use the auth function to get the user from the real database
    user = auth.get_user(db, form_data.username)

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # (The rest of the function remains the same)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}




# --- NEW ENDPOINT: For fetching latest performance metrics ---
@admin_router.get("/performance/latest")
@limiter.limit("30/minute")
async def get_latest_performance_metrics(
    request: Request,
    k: int = Query(10, ge=1, le=100, description="The number of latest claims to fetch."),
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user),
):
    """
    Fetches the performance metrics for the last K claims processed.
    Accessible only by admin users.
    """
    logs = crud.get_latest_performance_logs(db, limit=k)
    # print(logs)
    return logs


