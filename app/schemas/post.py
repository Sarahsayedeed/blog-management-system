from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 1. Base Schema: Contains fields shared across multiple schemas
class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, description="Title of the blog post")
    body: str = Field(..., min_length=10, description="Main content of the blog post")

    # Edge case: prevent whitespace-only values
    @field_validator("title", "body")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank or whitespace only")
        return v.strip()
# 2. Create Schema: Used for POST /posts
# Inherits title and body from PostBase. We don't ask the user for author_id 
# because we will securely extract that from their JWT token later.
class PostCreate(PostBase):
    pass

# 3. Update Schema: Used for PUT /posts/{id}
# All fields are Optional because a user might only want to update the title, 
# or only the body, but not necessarily both.
class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    body: Optional[str] = Field(None, min_length=10)

    # Edge case: whitespace-only in partial update
    @field_validator("title", "body")
    @classmethod
    def must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be blank or whitespace only")
        return v.strip() if v else v


# 4. Response Schema: Used when sending data back to the client
# Inherits title and body, but adds database-generated fields like ID and timestamps.
class PostResponse(PostBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # This configuration is crucial. It tells Pydantic to read the data 
    # even if it is not a standard dictionary (i.e., reading directly from an SQLAlchemy model).
    class Config:
        from_attributes = True  # Note: Use `orm_mode = True` if your project uses Pydantic V1
