from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import decode_access_token
from app.services.user_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Token validation failed: Invalid or expired token")
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        logger.warning("Token validation failed: Missing subject (sub) in token")
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Token validation failed: Invalid user ID format in token: {user_id_str}")
        raise credentials_exception

    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        logger.warning(f"Token validation failed: User ID {user_id} not found in database")
        raise credentials_exception
        
    logger.debug(f"Token validated for user ID {user_id}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}. "
                       f"Your role: {current_user.role.value}",
            )
        return current_user

    return role_checker


def verify_ownership(current_user: User, owner_user_id: int) -> None:
    """Verify the current user is allowed to modify a resource.

    Used by routes to enforce that authors can only modify their own posts,
    while admins can modify any post.
    """

    if current_user.role == UserRole.ADMIN:
        return

    if current_user.id != owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this resource",
        )