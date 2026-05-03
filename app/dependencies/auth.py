from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import decode_access_token
from app.services.user_service import get_user_by_id
from app.core.logging import logger
from app.database import get_db
from app.models.post import Post
from app.models.user import User

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


def verify_ownership(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this post"
        )
        
    return post