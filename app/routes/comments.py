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
async def add_comment(post_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    comment = comment_service.create_comment(db, data.body, current_user.id, post_id)
    
    await delete_cache_pattern(f"post:{post_id}:comments:*")
    
    return comment

@router.post("/comments/{comment_id}/reply", response_model=CommentResponse, status_code=201)
async def reply_to_comment(comment_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    parent = comment_service.get_comment_by_id(db, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment = comment_service.create_comment(db, data.body, current_user.id, parent.post_id, parent_comment_id=comment_id)
    
    await delete_cache_pattern(f"post:{parent.post_id}:comments:*")
    
    return comment

@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(post_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    cache_key = f"post:{post_id}:comments:skip_{skip}:limit_{limit}"
    
    try:
        cached_comments = await get_cache(cache_key)
        if cached_comments:
            print("\n  the data comes from REDIS CACHE  \n")
            if isinstance(cached_comments, str):
                cached_comments = json.loads(cached_comments)
            return cached_comments
    except Exception as e:
        print(f"Redis error: {e}")

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
async def update_comment(comment_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    
    updated_comment = comment_service.update_comment(db, comment, data.body)
    
    await delete_cache_pattern(f"post:{comment.post_id}:comments:*")
    
    return updated_comment

@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    post_id = comment.post_id 
    comment_service.delete_comment(db, comment)
    
    await delete_cache_pattern(f"post:{post_id}:comments:*")
    return None