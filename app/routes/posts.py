from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.database import get_db
from app.models.post import Post
from app.models.user import User, UserRole
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.dependencies.auth import require_roles, verify_ownership
from app.core.logging import logger
from app.services.redis_cache import get_cache, set_cache, delete_cache_pattern

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

        # Cache Invalidation: The new post must appear in the lists
        await delete_cache_pattern("posts:all:*")
        
        logger.info(f"Created new post", extra={"post_id": new_post.id, "author_id": current_user.id})
        return new_post
    except Exception as e:
        logger.error(f"Failed to create post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[PostResponse])
async def list_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Edge case: pagination validation
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        
    cache_key = f"posts:all:skip_{skip}:limit_{limit}"

    # --- Step 1: Try to fetch from Redis cache first ---
    try:
        cached_posts = await get_cache(cache_key)
        if cached_posts:
            logger.info("Fetched posts list from REDIS CACHE", extra={"skip": skip, "limit": limit})
            return cached_posts
    except Exception as e:
        logger.warning(f"Redis lookup failed: {e}")

    # --- Step 2: Cache miss — fetch from DB ---
    try:
        posts = db.query(Post).offset(skip).limit(limit).all()

        # FIX: Convert SQLAlchemy objects to JSON-serializable dicts before caching.
        # Previously, raw ORM objects were passed to set_cache, which Redis can't serialize.
        await set_cache(cache_key, jsonable_encoder(posts), expire=300)

        logger.info("Fetched posts list from DB", extra={"skip": skip, "limit": limit, "count": len(posts)})
        return posts
    except Exception as e:
        logger.error(f"Failed to fetch posts list: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{id}", response_model=PostResponse)
async def get_post(id: int, db: Session = Depends(get_db)):
    cache_key = f"post:{id}"

    # --- Step 1: Try to fetch from Redis cache first ---
    try:
        cached_post = await get_cache(cache_key)
        if cached_post:
            logger.info(f"Fetched post {id} from REDIS CACHE")
            return cached_post
    except Exception as e:
        logger.warning(f"Redis lookup failed: {e}")

    # --- Step 2: Cache miss — fetch from DB ---
    try:
        db_post = db.query(Post).filter(Post.id == id).first()
        if not db_post:
            logger.warning(f"Post fetch failed: Not found", extra={"post_id": id})
            raise HTTPException(status_code=404, detail="Post not found")

        # FIX: Convert SQLAlchemy object to JSON-serializable dict before caching.
        # Previously, raw ORM objects were passed to set_cache, which Redis can't serialize.
        await set_cache(cache_key, jsonable_encoder(db_post), expire=600)

        logger.info("Fetched single post from DB", extra={"post_id": id})
        return db_post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error while fetching post {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{id}", response_model=PostResponse)
async def update_post(  # FIX: Changed from `def` to `async def` to support await calls below
    id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN))
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    verify_ownership(current_user, db_post.author_id)
     
    # Edge case: empty update body
    update_data = post_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        for key, value in update_data.items():
            setattr(db_post, key, value)
        db.commit()
        db.refresh(db_post)

        # FIX: Invalidate cache after update so stale data isn't returned.
        # Previously, the cache was never cleared on update, causing GET to return old data.
        await delete_cache_pattern(f"post:{id}")       # invalidate single post cache
        await delete_cache_pattern("posts:all:*")      # invalidate list cache

        logger.info(f"Updated post", extra={"post_id": id, "updated_fields": list(update_data.keys())})
        return db_post
    except Exception as e:
        logger.error(f"Failed to update post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(  # FIX: Changed from `def` to `async def` to support await calls below
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN))
):
    db_post = db.query(Post).filter(Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    verify_ownership(current_user, db_post.author_id)

    try:
        db.delete(db_post)
        db.commit()

        # FIX: Invalidate cache after delete so deleted post isn't returned from cache.
        # Previously, the cache was never cleared on delete, causing GET to return deleted data.
        await delete_cache_pattern(f"post:{id}")       # invalidate single post cache
        await delete_cache_pattern("posts:all:*")      # invalidate list cache

        logger.info(f"Deleted post", extra={"post_id": id, "deleted_by": current_user.id})
        return None
    except Exception as e:
        logger.error(f"Failed to delete post: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
