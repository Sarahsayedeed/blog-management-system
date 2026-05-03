# Tests — Blog Management System

End-to-end test suite for the FastAPI backend, built with **pytest** and **TestClient**.

## Rubric Compliance Checklist

Every bullet from the assignment's "API Testing" requirement is mapped to specific tests below.

| Rubric requirement | Where it's covered |
|---|---|
| Use pytest as the testing framework | `pytest.ini` + all `test_*.py` files |
| Use TestClient from FastAPI for HTTP-level testing | `conftest.py::client` fixture; every test |
| **Authentication functionality** | `test_auth.py` |
| └─ Registration | `TestRegistration` (4 tests) |
| └─ Login | `TestLogin` (4 tests) |
| └─ Token generation | `TestLogin::test_login_with_valid_credentials_returns_token` |
| └─ Token validation | `TestTokenValidation` (4 tests) |
| **Protected endpoints** | `test_authorization.py` + `test_auth.py` |
| └─ Unauthorized access blocked | `test_auth.py::test_me_requires_authentication`, `test_unauthenticated_cannot_list_users` |
| └─ Role-based restrictions enforced | `TestAdminOnlyEndpoints`, `TestPostCreationRoles`, `TestPostDeletionRoles` (10 tests) |
| **CRUD operations for major entities** | |
| └─ Posts CRUD | `test_posts.py::TestPostsCRUD` (5 tests, full Create/Read-all/Read-by-id/Update/Delete) |
| └─ Comments CRUD | `test_comments.py::TestCommentsCRUD` (5 tests) |
| └─ Users CRUD | `test_auth.py::TestUserCRUD` (4 tests) |
| **Business logic validation** | `test_business_logic.py` (classes named `TestBusinessLogicValidation_*`) |
| └─ Privilege escalation prevention | `TestBusinessLogicValidation_PrivilegeEscalation` |
| └─ Admin lockout prevention | `TestBusinessLogicValidation_AdminRoleManagement` |
| └─ Ownership boundaries | `TestBusinessLogicValidation_OwnershipBoundaries` |
| └─ State transitions | `TestBusinessLogicValidation_StateTransitions` |
| **Edge cases and error handling** | `test_edge_cases.py` |
| └─ Invalid inputs | `TestRegistrationEdgeCases` (5 tests) |
| └─ Missing resources | `TestNotFoundResources` (6 tests) |
| └─ Duplicate entries | `TestDuplicates` (2 tests) |
| └─ Malformed payloads | `TestRegistrationEdgeCases::test_completely_malformed_json_is_rejected` |
| └─ String/length validation | `TestStringValidation` (3 tests) |
| └─ Path parameter validation | `TestPathParamValidation` (2 tests) |
| **Tests in dedicated `tests/` directory** | This is that directory |
| **Clear naming conventions** | All files `test_*.py`, all functions `test_*`, classes `Test*` |

**Total: ~70 tests across 6 files.**

## File breakdown

| File | Owner | Scope |
|------|-------|-------|
| `test_auth.py` | Member 5 | Registration, login, JWT generation, token validation, User CRUD |
| `test_authorization.py` | Member 5 | Role-based access (admin/author/reader), ownership |
| `test_posts.py` | Member 5 | Posts CRUD happy paths |
| `test_comments.py` | Member 5 | Comments CRUD + nested replies + pagination |
| `test_edge_cases.py` | Member 6 | Invalid inputs, 404s, duplicates, malformed payloads |
| `test_business_logic.py` | Member 6 | Privilege escalation, ownership boundaries, role transitions |

## Test infrastructure

- **In-memory SQLite** instead of Postgres. Each test runs against a fresh database, so tests are isolated and fast (entire suite runs in <2s).
- **Schema reset between every test** via the auto-use `fresh_db` fixture in `conftest.py`.
- **Pre-built role fixtures**: every test file can request `admin_token`, `author_token`, `reader_token`, `second_reader_token` and skip the boilerplate of registering+logging in.
- **No Redis dependency** — tests don't touch the cache layer.

## How to run

### Install dependencies (once)

```bash
pip install pytest pytest-cov httpx
```

`httpx` is required by FastAPI's `TestClient`; the others speak for themselves.

### Run everything

From the project root:

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=app --cov-report=term-missing
```

To produce an HTML coverage report:

```bash
pytest --cov=app --cov-report=html
# open htmlcov/index.html in a browser
```

### Run a single file or test class

```bash
pytest tests/test_auth.py
pytest tests/test_auth.py::TestLogin
pytest tests/test_auth.py::TestLogin::test_login_with_wrong_password_returns_401
```

### Verbose output (helpful while debugging)

```bash
pytest -vv
```

## Running inside Docker

If you'd rather not install Python locally:

```bash
docker compose exec app pytest --cov=app --cov-report=term-missing
```

This runs the suite inside the already-running `blog_app` container.

## How the test database works

`tests/conftest.py` overrides FastAPI's `get_db` dependency to point at an in-memory SQLite engine. The schema is created fresh before each test and dropped after, so there's never bleed-through between tests. The production Postgres database is never touched.

The `engine` uses `StaticPool` so the in-memory database survives across the multiple connections a single request opens.

## Adding a new test

1. Pick the right file (or create `test_<feature>.py`).
2. Use existing fixtures: `client`, `admin_token`, `author_token`, `reader_token`.
3. Use `auth_headers(token)` from `conftest` to build the Authorization header.

Example:

```python
from tests.conftest import auth_headers

def test_my_new_feature(client, admin_token):
    response = client.get("/some/endpoint", headers=auth_headers(admin_token))
    assert response.status_code == 200
```
