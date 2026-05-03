from contextlib import asynccontextmanager  
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware

from app.database import engine, Base
from app.routes import auth
from app.routes import comments
from app.routes import posts

from app.models import User  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.comment import Comment  # noqa: F401

from app.services.redis_cache import check_redis_connection, redis_db

# Initialize structured JSON logging (loguru)
setup_logging()

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

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors =[]
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": errors},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )

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