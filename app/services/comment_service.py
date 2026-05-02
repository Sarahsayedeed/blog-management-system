from sqlalchemy.orm import Session
from app.models.comment import Comment
from app.schemas.comment import CommentCreate

def create_comment(db: Session, body: str, author_id: int, post_id: int, parent_comment_id=None):
    comment = Comment(body=body, author_id=author_id, post_id=post_id, parent_comment_id=parent_comment_id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

def get_comments_for_post(db: Session, post_id: int, skip: int = 0, limit: int = 10):
    # Only return TOP-LEVEL comments (parent_comment_id is None)
    # Their replies are loaded automatically via the relationship
    return db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.parent_comment_id == None
    ).offset(skip).limit(limit).all()

def get_comment_by_id(db: Session, comment_id: int):
    return db.query(Comment).filter(Comment.id == comment_id).first()

def update_comment(db: Session, comment: Comment, new_body: str):
    comment.body = new_body
    db.commit()
    db.refresh(comment)
    return comment

def delete_comment(db: Session, comment: Comment):
    db.delete(comment)
    db.commit()