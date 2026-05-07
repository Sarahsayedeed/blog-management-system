from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm          # ← ADD THIS
from sqlalchemy.orm import Session

from app.core.logging import logger

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    UserRoleUpdate,
)
from app.services.auth_service import verify_password, create_access_token
from app.services.user_service import (
    get_user_by_username,
    get_user_by_email,
    get_all_users,
    get_user_by_id,
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

    # SECURITY: Force role to READER for public registration.
    # Admin/Author roles can only be assigned by an existing admin.
    user_data.role = UserRole.READER

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
    logger.info("Login attempt", extra={"username": form_data.username})
    
    # OAuth2PasswordRequestForm has .username and .password fields
    user = get_user_by_username(db, form_data.username)  # ← CHANGED
    if not user:
        logger.warning("Login failed: User not found", extra={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):  # ← CHANGED
        logger.warning("Login failed: Invalid password", extra={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Login failed: Account deactivated", extra={"username": form_data.username})
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

    logger.info("Login successful", extra={"username": form_data.username, "user_id": user.id})
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

@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update a user's role (Admin only)",
)
def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    # Find target user
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    # Prevent admin from demoting themselves (avoid lockout)
    if target_user.id == current_user.id and role_data.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own admin role",
        )

    logger.info(
        "Role updated",
        extra={
            "admin_id": current_user.id,
            "target_user_id": user_id,
            "old_role": target_user.role.value,
            "new_role": role_data.role.value,
        },
    )

    # Update and save
    target_user.role = role_data.role
    db.commit()
    db.refresh(target_user)

    return target_user