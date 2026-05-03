from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)

from app.database import engine, Base
from app.routes import auth, comments, posts

from app.models import User  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.comment import Comment  # noqa: F401


# Initialize structured JSON logging (loguru)
setup_logging()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Blog Management System",
    description="A backend system for a blogging platform.",
    version="1.0.0",
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# Exception handlers (order matters: most specific first)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(auth.router)
app.include_router(comments.router)
app.include_router(posts.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Blog Management System API",
        "docs": "/docs",
        "version": "1.0.0",
    }