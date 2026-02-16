# 🧁 Kabul Sweets — Backend API

Production-ready FastAPI backend for the Kabul Sweets Afghan bakery e-commerce platform.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI + Uvicorn |
| **Database** | PostgreSQL 16 (async via asyncpg) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Cache/Queue** | Redis 7 |
| **Auth** | JWT (access + refresh tokens) |
| **Password Hashing** | Argon2 |
| **Containerization** | Docker + Docker Compose |

## Quick Start

### 1. Start Infrastructure (PostgreSQL + Redis)

```bash
docker compose up -d db redis
```

### Optional: Connect Frontends to Docker (Not Started by Default)

Both UI services are wired to the same Docker network and API service, but are
profile-gated so they do not run unless requested.

```bash
# Customer frontend (http://localhost:3000)
docker compose --profile frontend up frontend

# Admin frontend (http://localhost:3001)
docker compose --profile admin up admin_frontend
```

### 2. Install Python Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Seed Database

```bash
python -m app.seed
```

### 4. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Open the Docs

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@kabulsweets.com.au` | `Admin@2024!` |
| Customer | `customer@example.com` | `Customer@2024!` |

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes
│   │   ├── deps.py       # Auth dependencies (JWT, RBAC)
│   │   └── v1/           # Version 1 endpoints
│   │       ├── auth.py   # Register, login, refresh, logout
│   │       ├── health.py # Health checks
│   │       ├── users.py  # User management
│   │       └── router.py # Route aggregator
│   ├── core/             # Core infrastructure
│   │   ├── config.py     # Settings (from .env)
│   │   ├── database.py   # Async SQLAlchemy engine
│   │   ├── logging.py    # Structured logging
│   │   ├── rate_limiter.py # Redis rate limiting
│   │   ├── redis.py      # Redis connection
│   │   └── security.py   # Argon2 + JWT
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py       # User model (admin/customer roles)
│   │   └── audit_log.py  # Admin action audit log
│   ├── schemas/          # Pydantic request/response schemas
│   │   └── user.py       # User & auth schemas
│   ├── services/         # Business logic (Phase 3+)
│   ├── main.py           # FastAPI app factory
│   └── seed.py           # Database seeder
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docker-compose.yml    # PostgreSQL + Redis + API
├── Dockerfile            # Multi-stage production build
├── pyproject.toml        # Dependencies & config
└── .env                  # Environment variables
```

## API Endpoints

### Auth (`/api/v1/auth`)
- `POST /register` — Create customer account
- `POST /login` — Login (rate limited)
- `POST /refresh` — Refresh JWT tokens
- `POST /logout` — Revoke refresh token

### Users (`/api/v1/users`)
- `GET /me` — Get current profile
- `PATCH /me` — Update profile
- `POST /me/change-password` — Change password
- `GET /` — [Admin] List users
- `GET /count` — [Admin] User count
- `GET /{id}` — [Admin] Get user
- `POST /` — [Admin] Create user (any role)
- `PATCH /{id}/deactivate` — [Admin] Deactivate user
- `PATCH /{id}/activate` — [Admin] Activate user

### Health (`/api/v1`)
- `GET /health` — Full health check (DB + Redis)
- `GET /ping` — Lightweight ping
