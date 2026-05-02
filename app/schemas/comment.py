from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# What the client sends to create a comment
class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)

# What the server sends back
class CommentResponse(BaseModel):
    id: int
    body: str
    author_id: int
    post_id: int
    parent_comment_id: Optional[int] = None
    created_at: datetime
    replies: List["CommentResponse"] = []  # nested replies

    class Config:
        from_attributes = True

CommentResponse.model_rebuild()  # needed for the self-referencing