from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.dependencies.auth import require_author, verify_ownership

# --- ADDED: Import the custom logger ---
from app.logger import custom_logger as logger

router = APIRouter(
    prefix="/posts",
    tags=["Posts"]
)

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_author)
):
    """Create a new post. (Author or Admin only)"""
    logger.bind(user_id=current_user.id, title=post_in.title).debug("Attempting to create a new post")

    new_post = Post(
        title=post_in.title,
        body=post_in.body,
        author_id=current_user.id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # --- LOGGING: Successful Creation ---
    logger.bind(post_id=new_post.id, author_id=current_user.id).info("Post created successfully")
    return new_post

@router.get("/", response_model=List[PostResponse])
def get_posts(
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(get_db)
):
    """Retrieve all posts with pagination."""
    # --- LOGGING: Database Read (Bulk) ---
    logger.bind(skip=skip, limit=limit).debug("Fetching posts from database")
    
    posts = db.query(Post).offset(skip).limit(limit).all()
    
    logger.bind(count=len(posts)).info("Posts retrieved successfully")
    return posts

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int, 
    db: Session = Depends(get_db)
):
    """Retrieve a specific post by ID."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        # --- LOGGING: Resource Not Found ---
        logger.bind(post_id=post_id).warning("GET failed: Post not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
    logger.bind(post_id=post.id, author_id=post.author_id).info("Single post retrieved successfully")
    return post

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_author)
):
    """Update a post. Authors can update their own; Admins can update any."""
    logger.bind(post_id=post_id, user_id=current_user.id).debug("Attempting to update post")
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        # --- LOGGING: Update Failed (Not Found) ---
        logger.bind(post_id=post_id).warning("Update failed: Post not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Enforce Ownership Validation (Your auth middleware will throw 403 if it fails)
    verify_ownership(current_user, post.author_id)

    if post_update.title is not None:
        post.title = post_update.title
    if post_update.body is not None:
        post.body = post_update.body

    db.commit()
    db.refresh(post)
    
    # --- LOGGING: Successful Update ---
    logger.bind(post_id=post.id, user_id=current_user.id).info("Post updated successfully")
    return post

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_author)
):
    """Delete a post. Authors can delete their own; Admins can delete any."""
    logger.bind(post_id=post_id, user_id=current_user.id).debug("Attempting to delete post")
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        # --- LOGGING: Delete Failed (Not Found) ---
        logger.bind(post_id=post_id).warning("Delete failed: Post not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Enforce Ownership Validation
    verify_ownership(current_user, post.author_id)

    db.delete(post)
    db.commit()
    
    # --- LOGGING: Successful Deletion ---
    logger.bind(post_id=post_id, user_id=current_user.id).info("Post deleted successfully")
    return None