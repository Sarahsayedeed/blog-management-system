from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["john_doe"],
    )
    email: EmailStr = Field(
        ...,
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        examples=["strongpassword123"],
    )
    role: Optional[UserRole] = Field(default=UserRole.READER)


class UserLogin(BaseModel):
    username: str = Field(..., examples=["john_doe"])
    password: str = Field(..., examples=["strongpassword123"])


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


class MessageResponse(BaseModel):
    message: str