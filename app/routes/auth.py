from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm          # ← ADD THIS
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
)
from app.services.auth_service import verify_password, create_access_token
from app.services.user_service import (
    get_user_by_username,
    get_user_by_email,
    get_all_users,
    create_user,
)
from app.dependencies.auth import (
    get_current_active_user,
    require_roles,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── REGISTER (stays the same) ────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' is already taken",
        )

    existing_email = get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_data.email}' is already registered",
        )

    new_user = create_user(db, user_data)
    return new_user


# ─── LOGIN (FIXED — accepts form data for Swagger) ────────────

@router.post(
    "/login",
    response_model=Token,
    summary="Login and get JWT token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),   # ← CHANGED
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm has .username and .password fields
    user = get_user_by_username(db, form_data.username)  # ← CHANGED
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):  # ← CHANGED
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator.",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
        },
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")


# ─── GET CURRENT USER (stays the same) ────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# ─── LIST ALL USERS (stays the same) ──────────────────────────

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    users = get_all_users(db, skip=skip, limit=limit)
    return users