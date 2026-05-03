from fastapi import APIRouter, Depends, status
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import PostNotFoundError, UnauthorizedActionError, AppException
from app.database import get_db
from app.models.post import Post
from app.models.user import User, UserRole
from app.dependencies.auth import get_current_active_user, require_roles
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.core.logging import logger

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
):
    try:
        new_post = Post(**post.model_dump(), author_id=current_user.id)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        logger.bind(post_id=new_post.id, author_id=current_user.id).info("Created new post")
        return new_post
    except SQLAlchemyError as e:
        db.rollback()
        logger.bind(error=str(e)).error("Failed to create post")
        raise AppException(detail="Failed to create post")


@router.get("/", response_model=List[PostResponse])
async def list_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    posts = db.query(Post).offset(skip).limit(limit).all()
    logger.bind(skip=skip, limit=limit, count=len(posts)).info("Fetched posts list")
    return posts


@router.get("/{id}", response_model=PostResponse)
async def get_post(id: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        logger.bind(post_id=id).warning("Post fetch failed: Not found")
        raise PostNotFoundError()
    logger.bind(post_id=id).info("Fetched single post")
    return db_post


@router.put("/{id}", response_model=PostResponse)
async def update_post(
    id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        logger.bind(post_id=id).warning("Post update failed: Not found")
        raise PostNotFoundError()

    if current_user.role != UserRole.ADMIN and db_post.author_id != current_user.id:
        logger.bind(post_id=id, user_id=current_user.id).warning(
            "Post update failed: Unauthorized access"
        )
        raise UnauthorizedActionError(detail="Not authorized to edit this post")

    try:
        update_data = post_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
        db.commit()
        db.refresh(db_post)
        logger.bind(post_id=id, updated_fields=list(update_data.keys())).info("Updated post")
        return db_post
    except SQLAlchemyError as e:
        db.rollback()
        logger.bind(error=str(e)).error("Failed to update post")
        raise AppException(detail="Failed to update post")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        logger.bind(post_id=id).warning("Post deletion failed: Not found")
        raise PostNotFoundError()

    if current_user.role != UserRole.ADMIN and db_post.author_id != current_user.id:
        logger.bind(post_id=id, user_id=current_user.id).warning(
            "Post deletion failed: Unauthorized access"
        )
        raise UnauthorizedActionError(detail="Not authorized to delete this post")

    try:
        db.delete(db_post)
        db.commit()
        logger.bind(post_id=id, deleted_by=current_user.id).info("Deleted post")
        return None
    except SQLAlchemyError as e:
        db.rollback()
        logger.bind(error=str(e)).error("Failed to delete post")
        raise AppException(detail="Failed to delete post")