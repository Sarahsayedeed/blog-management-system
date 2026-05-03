"""
Shared pytest fixtures for the Blog Management System test suite.

Strategy:
- Use an in-memory SQLite database for isolation and speed.
- Override FastAPI's `get_db` dependency to point at the test database.
- Provide ready-made fixtures for users of each role (admin, author, reader)
  along with their JWT tokens, so each test file can simply request
  `admin_token` / `author_token` / `reader_token` and start asserting.

This file is auto-discovered by pytest. Every fixture defined here is
available in every test_*.py file without extra imports.
"""
import os

# Force any code path that reads the env to use SQLite in-memory before
# the application modules are imported.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"  # not used in tests
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


# ─── Test database setup ──────────────────────────────────────

# StaticPool keeps the in-memory database alive across connections within
# a single test, which is essential because each request opens a new session.
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Replacement for the production get_db dependency."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def fresh_db():
    """
    Reset the schema before every test.

    autouse=True means this runs automatically for every test in the suite,
    so each test starts with a clean database. This eliminates ordering bugs.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Wire the test DB into the FastAPI app once, at module import.
app.dependency_overrides[get_db] = override_get_db


# ─── Test client ──────────────────────────────────────────────

@pytest.fixture
def client():
    """A TestClient that hits the FastAPI app in-process (no real network)."""
    with TestClient(app) as c:
        yield c


# ─── User-creation helpers ────────────────────────────────────

def _make_user(username: str, email: str, password: str, role: UserRole) -> User:
    """Insert a user directly into the test DB. Bypasses the public registration
    endpoint so we can create author/admin users (which the public API forbids)."""
    db = TestingSessionLocal()
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def admin_user():
    return _make_user("admin_test", "admin@test.com", "adminpass123", UserRole.ADMIN)


@pytest.fixture
def author_user():
    return _make_user("author_test", "author@test.com", "authorpass123", UserRole.AUTHOR)


@pytest.fixture
def reader_user():
    return _make_user("reader_test", "reader@test.com", "readerpass123", UserRole.READER)


@pytest.fixture
def second_reader():
    """A second reader, useful for ownership / cross-user tests."""
    return _make_user("reader_two", "reader2@test.com", "readerpass123", UserRole.READER)


# ─── Token helpers ────────────────────────────────────────────

def _login_and_get_token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    return _login_and_get_token(client, "admin_test", "adminpass123")


@pytest.fixture
def author_token(client, author_user):
    return _login_and_get_token(client, "author_test", "authorpass123")


@pytest.fixture
def reader_token(client, reader_user):
    return _login_and_get_token(client, "reader_test", "readerpass123")


@pytest.fixture
def second_reader_token(client, second_reader):
    return _login_and_get_token(client, "reader_two", "readerpass123")


# ─── Header helpers ───────────────────────────────────────────

def auth_headers(token: str) -> dict:
    """Convenience helper for tests; pass the resulting dict to client requests."""
    return {"Authorization": f"Bearer {token}"}
