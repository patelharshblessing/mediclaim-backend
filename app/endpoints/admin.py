# app/endpoints/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, pydantic_schemas, auth
from ..database import get_db

admin_router = APIRouter()

# --- User Management Endpoints ---
@admin_router.post("/users", response_model=pydantic_schemas.User, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user: pydantic_schemas.UserCreate, 
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    db_user = crud.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    return crud.create_user(db=db, user=user)

@admin_router.get("/users", response_model=List[pydantic_schemas.User])
def read_all_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@admin_router.put("/users/{user_id}", response_model=pydantic_schemas.User)
def update_existing_user(
    user_id: int,
    user_update: pydantic_schemas.UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --- Policy Management Endpoints ---

@admin_router.get("/policies", response_model=List[pydantic_schemas.Policy])
def read_all_policies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    policies = crud.get_policies(db, skip=skip, limit=limit)
    return policies

@admin_router.get("/policies/{policy_id}", response_model=pydantic_schemas.Policy)
def read_specific_policy(
    policy_id: str, 
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    db_policy = crud.get_policy_by_id(db, policy_id=policy_id)
    if db_policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db_policy

@admin_router.put("/policies/{policy_id}", response_model=pydantic_schemas.Policy)
def update_existing_policy(
    policy_id: str,
    policy_update: pydantic_schemas.Policy,
    db: Session = Depends(get_db),
    current_admin: pydantic_schemas.User = Depends(auth.get_current_admin_user)
):
    db_policy = crud.update_policy(db, policy_id=policy_id, policy_update=policy_update)
    if db_policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db_policy

