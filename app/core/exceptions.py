from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Any


# ============ Error Response Schema ============
class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    errors: list[dict[str, Any]] | None = None


# ============ Custom Business Exceptions ============
class AppException(Exception):
    """Base exception for all custom app errors."""
    status_code: int = 500
    error_code: str = "internal_error"
    detail: str = "An error occurred"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class PostNotFoundError(AppException):
    status_code = 404
    error_code = "post_not_found"
    detail = "Post not found"


class CommentNotFoundError(AppException):
    status_code = 404
    error_code = "comment_not_found"
    detail = "Comment not found"


class UserNotFoundError(AppException):
    status_code = 404
    error_code = "user_not_found"
    detail = "User not found"


class UnauthorizedActionError(AppException):
    status_code = 403
    error_code = "unauthorized_action"
    detail = "You are not authorized to perform this action"


class DuplicateResourceError(AppException):
    status_code = 400
    error_code = "duplicate_resource"
    detail = "Resource already exists"


# ============ Exception Handlers ============
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=exc.error_code,
        ).model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=str(exc.detail),
            error_code=f"http_{exc.status_code}",
        ).model_dump(exclude_none=True),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="Validation Error",
            error_code="validation_error",
            errors=errors,
        ).model_dump(exclude_none=True),
    )


async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An unexpected error occurred.",
            error_code="internal_server_error",
        ).model_dump(exclude_none=True),
    )