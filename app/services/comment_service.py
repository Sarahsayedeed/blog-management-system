from sqlalchemy.orm import Session
from app.models.comment import Comment
from fastapi import HTTPException, status

# Maximum allowed nesting depth for replies (reply → reply → reply = depth 3)
MAX_NESTING_DEPTH = 3


def create_comment(db: Session, body: str, author_id: int,
                   post_id: int, parent_comment_id=None):
    # Edge case: reject whitespace-only body
    if not body or not body.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment body cannot be empty"
        )

    # Edge case: prevent deeply nested replies beyond MAX_NESTING_DEPTH
    # calculates how deep the parent comment already is before allowing the reply
    if parent_comment_id is not None:
        depth = _get_depth(db, parent_comment_id)
        if depth >= MAX_NESTING_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum comment nesting depth ({MAX_NESTING_DEPTH}) reached"
            )

    # Strip whitespace from body before saving
    comment = Comment(
        body=body.strip(),
        author_id=author_id,
        post_id=post_id,
        parent_comment_id=parent_comment_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments_for_post(db: Session, post_id: int,
                           skip: int = 0, limit: int = 10):
    # Edge case: sanitize pagination values to safe ranges
    # skip cannot be negative, limit is capped at 100
    skip = max(0, skip)
    limit = max(1, min(limit, 100))

    # Only fetch top-level comments (parent_comment_id is None)
    # nested replies are loaded automatically via SQLAlchemy relationship
    return db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.parent_comment_id == None
    ).offset(skip).limit(limit).all()


def get_comment_by_id(db: Session, comment_id: int):
    return db.query(Comment).filter(Comment.id == comment_id).first()


def update_comment(db: Session, comment: Comment, new_body: str):
    # Edge case: reject whitespace-only body on update
    if not new_body or not new_body.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment body cannot be empty"
        )
    # Strip whitespace before saving
    comment.body = new_body.strip()
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: Comment):
    # Edge case: cascade delete — remove all nested replies before deleting the comment
    # Comment model does not have cascade="all, delete-orphan" on replies relationship
    # so we handle it manually to avoid orphaned replies in the DB
    _delete_recursive(db, comment)
    db.commit()


def _delete_recursive(db: Session, comment: Comment):
    # Fetch all direct replies to this comment
    replies = db.query(Comment).filter(
        Comment.parent_comment_id == comment.id
    ).all()
    # Recursively delete each reply and its own nested replies first
    for reply in replies:
        _delete_recursive(db, reply)
    # Then delete the comment itself
    db.delete(comment)


def _get_depth(db: Session, comment_id: int, depth: int = 0) -> int:
    # Walk up the parent chain counting levels
    # returns 0 if comment is top-level, 1 if reply, 2 if reply-to-reply, etc.
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.parent_comment_id is None:
        return depth
    return _get_depth(db, comment.parent_comment_id, depth + 1)
