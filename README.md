
```markdown
# Blog Management System — Backend API

## 👤 Person 1: Project Setup & Auth Foundation

### What I Built (Phase 1)
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
│   │   ├── user.py              # Users table
│   │   └── post.py              # Posts table
│   │
│   ├── schemas/                 # Request/Response validation
│   │   ├── __init__.py
│   │   ├── user.py              # What data looks like in API
│   │   └── post.py              # Post validation schemas
│   │
│   ├── services/                # Business logic & Integrations
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Password hashing + JWT tokens
│   │   ├── user_service.py      # Database operations for users
│   │   └── redis_cache.py       # Redis connection & caching utilities
│   │
│   ├── routes/                  # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py              # /auth/register, /auth/login, etc.
│   │   ├── posts.py             # /posts endpoints (with caching)
│   │   └── comments.py          # /comments endpoints
│   │
│   └── dependencies/            # Shared security guards
│       ├── __init__.py
│       └── auth.py              # Token validation + role checking
│
├── Dockerfile                   # Docker image configuration
├── docker-compose.yml           # Docker services (app + database + redis)
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
git clone https://github.com/Sarahsayedeed/blog-management-system.git
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
# REDIS_URL=redis://localhost:6379/0

# 6. Ensure Redis is running locally (Important for Caching)

# 7. Run the server
uvicorn app.main:app --reload

# 8. Open browser
# http://localhost:8000/docs
```

### Option 2: With Docker (Recommended)

```bash
# This will spin up the API, DB, Redis, and Monitoring tools
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

*(Refer to Swagger UI `/docs` for Posts and Comments endpoints)*

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
Server validates input (Pydantic) → checks duplicates
    ↓
Server hashes password (bcrypt) → saves user to DB
```

### Login Flow:
```
Client sends: username + password
    ↓
Server verifies password against hash
    ↓
Server creates JWT token with: user_id + username + role
```

### Protected Route Flow:
```
Client sends header: Authorization: Bearer eyJ...
    ↓
get_current_user extracts & decodes token → fetches User from DB
    ↓
require_roles checks role → Proceeds or returns 401/403
```

---

## 🧠 Member 1 (Phase 2): Redis Caching Layer

### What I Built
Implemented the **Cache-Aside Pattern** using Redis to drastically optimize read-heavy endpoints (GET requests) and reduce database load.

### 🔑 Cache Keys Naming Convention
To ensure consistency and allow easy cache invalidation, we follow this naming convention: `entity:scope:parameters`

| Entity   | Endpoint | Cache Key Format | Example |
|----------|----------|-------------------|---------|
| **Posts** | GET All Posts | `posts:all:skip_{skip}:limit_{limit}` | `posts:all:skip_0:limit_10` |
| **Posts** | GET Post by ID | `post:{id}` | `post:15` |

### 🛠️ For Team Members: How to Use Cache (Member 2)

I have created utility functions in `app/services/redis_cache.py` for you to implement **Cache Invalidation**:

```python
from app.services.redis_cache import delete_cache, delete_cache_pattern

# 1. When a new post is CREATED (Clear paginated lists)
await delete_cache_pattern("posts:all:*")

# 2. When a specific post is UPDATED or DELETED (Clear specific item)
await delete_cache(f"post:{post_id}")
```

---

## 🔧 For Team Members: How to Use Auth Logic

### Import these in your routes:

```python
from app.dependencies.auth import get_current_active_user, require_roles
from app.database import get_db
from app.models.user import User, UserRole
```

### Example: Admin-only endpoint

```python
@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    return {"message": "Post deleted"}
```

---

## 📂 File-by-File Explanation

- **`app/config.py`**: Reads settings from `.env`.
- **`app/database.py`**: DB connection setup.
- **`app/models/*.py`**: Database tables (SQLAlchemy).
- **`app/schemas/*.py`**: Request/Response validation (Pydantic).
- **`app/services/auth_service.py`**: Hashing and JWT generation.
- **`app/services/redis_cache.py`**: Redis logic (get, set, delete).
- **`app/dependencies/auth.py`**: Guards for token and role validation.

---

## 📊 Monitoring Dashboard (Member 4)

### Stack
- **Prometheus** → Collects API metrics
- **Grafana** → Visualizes the metrics

### Setup
Run everything with one command:
```bash
docker-compose up --build
```

### Access
| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Metrics | http://localhost:8000/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

### Grafana Login
- Username: `admin`
- Password: `admin`

### Dashboard Panels
1. **API Request Counts** → Total requests per endpoint
2. **Response Times** → How fast the API responds
3. **Error Rates** → Failed requests tracking
4. **System Health** → API uptime status

### Data Source
- Add Prometheus as data source: `http://prometheus:9090`
```