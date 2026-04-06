# Blog Management System — Backend API

## 👤 Person 1: Project Setup & Auth Foundation

### What I Built
I built the **foundation** of the entire project. Everything other team members
build will use my code as the base.

---

## 📁 Project Structure

```
blog_management/
│
├── app/
│   ├── __init__.py              # Makes 'app' a Python package
│   ├── main.py                  # App entry point — starts FastAPI
│   ├── config.py                # Reads settings from .env file
│   ├── database.py              # Database connection setup
│   │
│   ├── models/                  # Database table definitions
│   │   ├── __init__.py
│   │   └── user.py              # Users table
│   │
│   ├── schemas/                 # Request/Response validation
│   │   ├── __init__.py
│   │   └── user.py              # What data looks like in API
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Password hashing + JWT tokens
│   │   └── user_service.py      # Database operations for users
│   │
│   ├── routes/                  # API endpoints
│   │   ├── __init__.py
│   │   └── auth.py              # /auth/register, /auth/login, etc.
│   │
│   └── dependencies/            # Shared security guards
│       ├── __init__.py
│       └── auth.py              # Token validation + role checking
│
├── Dockerfile                   # Docker image configuration
├── docker-compose.yml           # Docker services (app + database)
├── .dockerignore                # Files excluded from Docker
├── .env                         # Environment variables (DO NOT COMMIT)
├── .gitignore                   # Files excluded from Git
└── requirements.txt             # Python packages
```

---

## 🚀 How to Run the Project

### Option 1: Local (Without Docker)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/blog-management-system.git
cd blog-management-system

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install packages
pip install -r requirements.txt

# 5. Create .env file
# Copy the .env.example or create .env with:
# DATABASE_URL=sqlite:///./blog.db
# SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
# ALGORITHM=HS256
# ACCESS_TOKEN_EXPIRE_MINUTES=30

# 6. Run the server
uvicorn app.main:app --reload

# 7. Open browser
# http://localhost:8000/docs
```

### Option 2: With Docker

```bash
docker compose up --build
# Open: http://localhost:8000/docs
```

---

## 📡 API Endpoints

| Method | Endpoint         | Auth Required | Role Required | Description              |
|--------|------------------|---------------|---------------|--------------------------|
| GET    | /                | No            | None          | Health check             |
| POST   | /auth/register   | No            | None          | Register new user        |
| POST   | /auth/login      | No            | None          | Login + get JWT token    |
| GET    | /auth/me         | Yes           | Any           | Get current user profile |
| GET    | /auth/users      | Yes           | Admin only    | List all users           |

---

## 👥 User Roles

| Role   | Description                    |
|--------|--------------------------------|
| admin  | Full moderation control        |
| author | Create and manage own posts    |
| reader | View and comment (default)     |

---

## 🔐 How Authentication Works

### Registration Flow:
```
Client sends: username + email + password + role(optional)
    ↓
Server validates input (Pydantic)
    ↓
Server checks for duplicate username/email
    ↓
Server hashes password (bcrypt)
    ↓
Server saves user to database
    ↓
Server returns user info (without password)
```

### Login Flow:
```
Client sends: username + password
    ↓
Server finds user by username
    ↓
Server verifies password against hash
    ↓
Server creates JWT token with: user_id + username + role
    ↓
Server returns: { access_token: "eyJ...", token_type: "bearer" }
```

### Protected Route Flow:
```
Client sends request with header: Authorization: Bearer eyJ...
    ↓
get_current_user dependency extracts token
    ↓
Token is decoded and verified
    ↓
User is fetched from database
    ↓
If role check needed → require_roles checks the role
    ↓
Request proceeds or returns 401/403 error
```

---

## 🔧 For Team Members: How to Use My Code

### Import these in your routes:

```python
# To protect a route (user must be logged in)
from app.dependencies.auth import get_current_active_user

# To restrict by role
from app.dependencies.auth import require_roles

# To access database
from app.database import get_db

# To use User model and roles
from app.models.user import User, UserRole
```

### Example: Protect your endpoint (any logged-in user)

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/posts")
def get_posts(current_user: User = Depends(get_current_active_user)):
    # Only logged-in users can access this
    # current_user contains the user's info
    return {"message": f"Hello {current_user.username}"}
```

### Example: Admin-only endpoint

```python
from app.dependencies.auth import require_roles
from app.models.user import UserRole

@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    # Only admins can delete posts
    return {"message": "Post deleted"}
```

### Example: Author can manage own content

```python
@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AUTHOR))
):
    # Admin OR Author can update
    return {"message": "Post updated"}
```

### How to add your router to the app:

```python
# In app/main.py, add:
from app.routes import posts     # your new router file
app.include_router(posts.router)
```

---

## 📂 File-by-File Explanation

### app/config.py
Reads settings from .env file. Every other file uses `settings` from here.

### app/database.py
Creates database connection. Provides `get_db` dependency for routes.
Works with both SQLite (local) and PostgreSQL (Docker).

### app/models/user.py
Defines the Users database table with columns:
- id, username, email, hashed_password, role, is_active, created_at, updated_at

### app/schemas/user.py
Defines what data looks like in requests and responses:
- UserCreate: what client sends for registration
- UserLogin: what client sends for login
- UserResponse: what server returns (never includes password)
- Token: JWT token response

### app/services/auth_service.py
- hash_password(): Converts plain password to bcrypt hash
- verify_password(): Checks if password matches hash
- create_access_token(): Creates a JWT token
- decode_access_token(): Reads and validates a JWT token

### app/services/user_service.py
Database operations: create user, find by id/username/email, list all users.

### app/dependencies/auth.py
Security guards:
- get_current_user: Validates JWT → returns User object
- get_current_active_user: Same + checks if account is active
- require_roles(): Checks if user has the required role

### app/routes/auth.py
API endpoints: register, login, get profile, list users.

### app/main.py
Entry point: creates FastAPI app, adds middleware, registers routes,
creates database tables, handles errors.
