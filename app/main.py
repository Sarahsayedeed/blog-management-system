from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

from app.services.redis_cache import check_redis_connection, redis_db


# Initialize structured JSON logging (loguru)
setup_logging()

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Redis
    await check_redis_connection()
    yield
    # Shutdown: Close Redis connection
    await redis_db.close()


app = FastAPI(
    title="Blog Management System",
    description="A backend system for a blogging platform.",
    version="1.0.0",
    lifespan=lifespan,
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

# Global exception handlers (most specific first)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(auth.router)
app.include_router(comments.router)
app.include_router(posts.router)

# Serve the HTML/CSS/JS frontend (same-origin)
_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")
app.mount("/ui", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="ui")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Blog Management System API",
        "docs": "/docs",
        "ui": "/ui",
        "version": "1.0.0",
    }
