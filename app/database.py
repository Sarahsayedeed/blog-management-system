from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def _create_engine():
    if settings.DATABASE_URL.startswith("sqlite"):
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        return create_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()