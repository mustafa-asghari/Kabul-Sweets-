# Production Readiness Audit

This document outlines potential issues, missing features, and recommendations for taking the **Kabul Sweets** project to production.

## 🚨 Critical Issues (Must Fix)

### 1. Missing Dependencies
- **Issue**: The `backend/requirements.txt` (or mechanism) imports `sentry_sdk` in `app/core/monitoring.py`, but it is **not listed** in `backend/pyproject.toml`.
- **Impact**: Error tracking will fail silently, and you won't be notified of crashes in production.
- **Fix**: Add `"sentry-sdk[fastapi,sqlalchemy]>=2.0.0"` to `backend/pyproject.toml`.

### 2. Inconsistent Configuration
- **Issue**: `backend/app/core/config.py` defines a `Settings` class using Pydantic, but it **omits** many critical environment variables used elsewhere (e.g., `SMTP_*`, `MAILGUN_*`, `STRIPE_*`, `GEMINI_*`).
- **Impact**: The application relies on `os.getenv()` scattered throughout the code with hardcoded defaults. If an extensive variable is missing in production, the app will start but fail at runtime (e.g., when sending an email), rather than failing fast at startup with a clear error.
- **Fix**: comprehensive `Settings` model in `config.py` to validate all required env vars.

### 3. Missing Frontend Optimization
- **Issue**: The `admin_frontend` uses Next.js Image component but lacks the `sharp` library.
- **Impact**: Image optimization will be slow or fallback to unoptimized images, hurting performance.
- **Fix**: Add `sharp` to `admin_frontend/mantine-analytics-dashboard/package.json`.

### 4. Database Migrations in Production
- **Issue**: `backend/app/main.py` explicitly skips table creation (`create_all`) when `APP_ENV=production`.
- **Impact**: If you deploy a fresh database or update the schema, the app will crash because tables won't exist.
- **Fix**: Ensure your deployment pipeline runs `alembic upgrade head` before starting the API.

## ⚠️ Architectural & DevOps Gaps

### 5. No Reverse Proxy (SSL/HTTPS)
- **Issue**: The `docker-compose.yml` exposes services on ports `8000`, `3000`, `3001` directly.
- **Impact**: No SSL termination (HTTPS), no unified domain routing (e.g., `api.domain.com` vs `domain.com`).
- **Fix**: Add an Nginx or Traefik container to handle SSL and route requests to the correct containers on an internal network.

### 6. Database Backups
- **Issue**: There is no automated backup strategy for the PostgreSQL database.
- **Impact**: Risk of total data loss if the volume is corrupted or deleted.
- **Fix**: Add a scheduled backup container (e.g., `pg_dump` to S3) in `docker-compose.yml`.

### 7. In-Memory Rate Limiting
- **Issue**: `IPThrottleMiddleware` stores request counts in Python memory.
- **Impact**: If you scale the API to multiple replicas (horizontal scaling), rate limits will not be shared, allowing users to bypass limits.
- **Fix**: Use Redis for rate limiting (FastAPI-Limiter or similar).

### 8. Image Storage in Database
- **Issue**: Images are stored as Base64 text in the PostgreSQL database (`ProcessedImage.original_url`).
- **Impact**: This will cause the database size to balloon rapidly, slowing down backups and migrations.
- **Fix**: Store images in object storage (AWS S3, Google Cloud Storage, Cloudflare R2) and save only the URL in the database.

## 🔍 Code Quality & Best Practices

### 9. Hardcoded "Public" Paths
- **Issue**: `middleware.ts` in the frontend has hardcoded paths.
- **Fix**: Centralize route definitions.

### 10. Logging
- **Suggestion**: Ensure logs are shipped to a centralized logging service (e.g., Datadog, CloudWatch, or just retained text files) as Docker logs rotate and are lost on container recreation.

## ✅ Action Plan

1.  **Immediate**: Fix `pyproject.toml` and `package.json` dependencies.
2.  **Immediate**: Update `config.py` to validate all env vars.
3.  **Deployment**: Create a `production.yml` (docker-compose override) that includes Nginx.
4.  **Deployment**: Set up a database backup cron job.
