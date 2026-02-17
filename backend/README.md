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

### 1. Configure Environment

```bash
cp .env.example .env
```

Fill all required values in `.env` (database, Redis, JWT secrets, URLs, etc.).

### 2. Start Infrastructure (PostgreSQL + Redis + Workers)

```bash
docker compose up -d db redis api celery_worker celery_beat
```

Note: `docker-compose.yml` uses `DOCKER_*` URL variables for container-to-container
connections, so your local `DATABASE_URL=...localhost...` and `REDIS_URL=...localhost...`
can still be used when running the API directly on your machine.

### Optional: Connect Frontends to Docker (Not Started by Default)

Both UI services are wired to the same Docker network and API service, but are
profile-gated so they do not run unless requested.

```bash
# Customer frontend (http://localhost:3000)
docker compose --profile frontend up frontend

# Admin frontend (http://localhost:3001)
docker compose --profile admin up admin_frontend
```

### 3. Install Python Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Seed Database

```bash
python -m app.seed
```

Note: user seeding now comes from env vars (`SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`,
`SEED_DEMO_CUSTOMERS_JSON`, etc.) rather than hardcoded credentials.

### 4.1 Create Admin Safely (No Direct DB Insert)

Do not insert users directly in SQL. Use the provisioning command so passwords
are hashed with Argon2 and role/flags are set correctly.

```bash
# Create a new admin (prompts for password securely)
python -m app.create_admin --email admin@kabulsweets.com.au --full-name "Kabul Admin"

# Promote an existing user to admin and reset their password
python -m app.create_admin \
  --email existing@kabulsweets.com.au \
  --promote-existing \
  --reset-password
```

### 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Open the Docs

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

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
│   ├── seed.py           # Database seeder
│   └── create_admin.py   # Secure admin provisioning utility
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
