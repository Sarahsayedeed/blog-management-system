from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

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
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN))
):
    try:
        new_post = Post(**post.model_dump(), author_id=current_user.id)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        logger.info(f"Created new post", extra={"post_id": new_post.id, "author_id": current_user.id})
        return new_post
    except Exception as e:
        logger.error(f"Failed to create post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/", response_model=List[PostResponse])
async def list_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        posts = db.query(Post).offset(skip).limit(limit).all()
        logger.info("Fetched posts list", extra={"skip": skip, "limit": limit, "count": len(posts)})
        return posts
    except Exception as e:
        logger.error(f"Failed to fetch posts list: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/{id}", response_model=PostResponse)
async def get_post(id: int, db: Session = Depends(get_db)):
    try:
        db_post = db.query(Post).filter(Post.id == id).first()
    except Exception as e:
        logger.error(f"Database error while fetching post {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
        
    if not db_post:
        logger.warning(f"Post fetch failed: Not found", extra={"post_id": id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
    logger.info("Fetched single post", extra={"post_id": id})
    return db_post

@router.put("/{id}", response_model=PostResponse)
async def update_post(
    id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN))
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        logger.warning(f"Post update failed: Not found", extra={"post_id": id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
    if current_user.role != UserRole.ADMIN and db_post.author_id != current_user.id:
        logger.warning(f"Post update failed: Unauthorized access", extra={"post_id": id, "user_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this post")

    try:
        update_data = post_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
            
        db.commit()
        db.refresh(db_post)
        logger.info(f"Updated post", extra={"post_id": id, "updated_fields": list(update_data.keys())})
        return db_post
    except Exception as e:
        logger.error(f"Failed to update post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN))
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        logger.warning(f"Post deletion failed: Not found", extra={"post_id": id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
    if current_user.role != UserRole.ADMIN and db_post.author_id != current_user.id:
        logger.warning(f"Post deletion failed: Unauthorized access", extra={"post_id": id, "user_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this post")

    try:
        db.delete(db_post)
        db.commit()
        logger.info(f"Deleted post", extra={"post_id": id, "deleted_by": current_user.id})
        return None
    except Exception as e:
        logger.error(f"Failed to delete post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
