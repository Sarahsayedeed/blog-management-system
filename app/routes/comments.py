from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse
import app.services.comment_service as comment_service

router = APIRouter(tags=["Comments"])

# 1. Add a comment to a post (any logged-in user)
@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(post_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return comment_service.create_comment(db, data.body, current_user.id, post_id)

# 2. Reply to a comment (nested comment)
@router.post("/comments/{comment_id}/reply", response_model=CommentResponse, status_code=201)
def reply_to_comment(comment_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    parent = comment_service.get_comment_by_id(db, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment_service.create_comment(db, data.body, current_user.id, parent.post_id, parent_comment_id=comment_id)

# 3. Get all comments for a post (with pagination)
@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def get_comments(post_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return comment_service.get_comments_for_post(db, post_id, skip, limit)

# 4. Edit own comment
@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    return comment_service.update_comment(db, comment, data.body)

# 5. Delete own comment or Admin deletes any
@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    comment_service.delete_comment(db, comment)