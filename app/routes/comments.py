from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User, UserRole
from app.schemas.comment import CommentResponse, CommentCreate
import app.services.comment_service as comment_service
from fastapi.encoders import jsonable_encoder
import json

from app.services.redis_cache import get_cache, set_cache, delete_cache_pattern

router = APIRouter(tags=["Comments"])


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # create the comment via service (body validation happens inside the service)
    comment = comment_service.create_comment(db, data.body, current_user.id, post_id)

    # Invalidate all cached comment lists for this post
    # so the next GET returns fresh data including the new comment
    await delete_cache_pattern(f"post:{post_id}:comments:*")

    return comment


@router.post("/comments/{comment_id}/reply", response_model=CommentResponse, status_code=201)
async def reply_to_comment(
    comment_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # fetch the parent comment to get its post_id for cache invalidation
    parent = comment_service.get_comment_by_id(db, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Comment not found")

    # service handles nesting depth check before creating the reply
    comment = comment_service.create_comment(
        db, data.body, current_user.id, parent.post_id, parent_comment_id=comment_id
    )

    # Invalidate comment list cache for the post this reply belongs to
    await delete_cache_pattern(f"post:{parent.post_id}:comments:*")

    return comment


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    post_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # PERSON A: Edge case — reject invalid pagination values
    # skip cannot be negative, limit must be between 1 and 100
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    cache_key = f"post:{post_id}:comments:skip_{skip}:limit_{limit}"

    # Step 1: try to get from Redis cache first (Cache-Aside Pattern)
    try:
        cached_comments = await get_cache(cache_key)
        if cached_comments:
            print("\n  the data comes from REDIS CACHE  \n")
            if isinstance(cached_comments, str):
                cached_comments = json.loads(cached_comments)
            return cached_comments
    except Exception as e:
        print(f"Redis error: {e}")

    # Step 2: cache miss — fetch from DB and store in cache
    print("\n the data comes from DB \n")
    comments = comment_service.get_comments_for_post(db, post_id, skip, limit)
    comments_data = jsonable_encoder(comments)

    try:
        await set_cache(cache_key, json.dumps(comments_data), expire=300)
        print("\n  Saved to REDIS cache \n")
    except Exception as e:
        print(f"Failed to save to Redis: {e}")

    return comments


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # fetch comment first to check ownership and get post_id for cache invalidation
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # ownership check — only the author can edit their own comment
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    # service handles whitespace validation before updating
    updated_comment = comment_service.update_comment(db, comment, data.body)

    # Invalidate all cached comment lists for this post after update
    await delete_cache_pattern(f"post:{comment.post_id}:comments:*")

    return updated_comment


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # fetch comment first to check ownership and get post_id for cache invalidation
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # only the author or an admin can delete a comment
    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    # save post_id before deletion since we need it for cache invalidation after
    post_id = comment.post_id

    # service handles recursive deletion of all nested replies
    comment_service.delete_comment(db, comment)

    # Invalidate all cached comment lists for this post after delete
    await delete_cache_pattern(f"post:{post_id}:comments:*")

    return None
