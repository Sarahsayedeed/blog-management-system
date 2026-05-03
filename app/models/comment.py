from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    body = Column(String, nullable=False)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)      # who wrote it
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)        # which post
    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)  # NULL = top-level, has value = it's a reply

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    replies = relationship("Comment", back_populates="parent")  # nested comments
    parent = relationship("Comment", back_populates="replies", remote_side=[id])