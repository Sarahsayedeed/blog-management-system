from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
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

# --- Redis Cache Utilities (Member 2 Task) ---
from app.services.redis_cache import get_cache, set_cache, delete_cache, delete_cache_pattern

router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- REGISTER (CREATE) ---

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # Set default role to READER
    user_data.role = UserRole.READER
    new_user = create_user(db, user_data)

    # 🔥 [Member 2] Cache Invalidation: Clear all user lists since a new user was added
    await delete_cache_pattern("users:all:*")
    logger.info("Cache invalidated for user lists due to new registration")

    return new_user


# --- LOGIN (Authentication) ---

@router.post("/login", response_model=Token, summary="Login and get JWT token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Special case for admin user (for testing/demo purposes)
    # if form_data.username == "sarah_admin" and form_data.password == "123456":
    #     access_token = create_access_token(
    #         data={"sub": "1", "username": "sarah_admin", "role": "admin"}
    #     )
    #     return Token(access_token=access_token, token_type="bearer")




    """Note: Login is read-only, no cache invalidation needed here."""
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


# --- GET ME (READ with Cache) ---

@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_active_user)):
    # 🔥 [Member 2] Cache Aside: Check if user profile is cached
    cache_key = f"user:{current_user.id}"
    cached_user = await get_cache(cache_key)
    if cached_user:
        return cached_user
    
    # If not in cache, store it for 10 minutes
    await set_cache(cache_key, current_user, expire=600)
    return current_user


# --- UPDATE PROFILE (UPDATE - Self) ---

@router.put("/me", response_model=UserResponse, summary="Update current user profile")
async def update_current_user(
    user_update: UserCreate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Update logic (Simplified: updating username and email)
    current_user.username = user_update.username
    current_user.email = user_update.email
    
    db.commit()
    db.refresh(current_user)

    # 🔥 [Member 2] Cache Invalidation (UPDATE):
    # 1. Clear the specific user cache
    await delete_cache(f"user:{current_user.id}")
    # 2. Clear all user lists to ensure the admin sees the updated info
    await delete_cache_pattern("users:all:*")
    
    logger.info(f"Cache invalidated for user {current_user.id} update")
    return current_user


# --- LIST ALL USERS (READ with Cache) ---

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    # 🔥 [Member 2] Cache Aside for lists
    cache_key = f"users:all:skip_{skip}:limit_{limit}"
    cached_users = await get_cache(cache_key)
    if cached_users:
        logger.info("Fetching users list from CACHE")
        return cached_users

    users = get_all_users(db, skip=skip, limit=limit)
    await set_cache(cache_key, users, expire=300)
    return users


# --- UPDATE USER ROLE (UPDATE - Admin) ---

@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update a user's role (Admin only)",
)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.role = role_data.role
    db.commit()
    db.refresh(target_user)

    # 🔥 [Member 2] Cache Invalidation (UPDATE):
    # Clear specific user cache and all user lists
    await delete_cache(f"user:{user_id}")
    await delete_cache_pattern("users:all:*")
    
    return target_user


# --- DELETE USER (DELETE - Admin) ---

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (Admin only)"
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot delete yourself")

    db.delete(target_user)
    db.commit()

    # 🔥 [Member 2] Cache Invalidation (DELETE):
    # Purge user profile cache and list cache
    await delete_cache(f"user:{user_id}")
    await delete_cache_pattern("users:all:*")
    
    logger.info(f"User {user_id} deleted and cache purged")
    return None