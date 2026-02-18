# Kabul Sweets

A modern e-commerce platform for ordering traditional Afghan sweets and custom cakes.

## Features

- **Authentication & RBAC**: Secure user authentication with Role-Based Access Control (Admin, Staff, Customer).
- **Custom Orders**: Specialized flow for ordering custom cakes with deposit payments.
- **Background Jobs**: Asynchronous task processing for emails, alerts, and analytics using Celery & Redis.
- **Analytics Dashboard**: Comprehensive insights into sales, inventory, and product performance.

## Getting Started

### Prerequisites

- Docker & Docker Compose

### Running the Application

1. **Clone the repository** (if you haven't already).
2. **Navigate to the root directory**.
3. **Start the services**:

   ```bash
   docker compose up --build
   ```

   This will start:
   - Backend API (http://localhost:8000)
   - Database (PostgreSQL)
   - Redis
   - Celery Worker & Beat
   - Frontend (http://localhost:3000) - *Note: Frontend requires the `frontend` profile or uncommenting in compose if you wish to run it simultaneously, but usually it's `npm run dev` in the frontend folder for dev.*
   - Admin Frontend (http://localhost:3001) - *Note: Requires `admin` profile (`docker compose --profile admin up`)*

### Development

- **Backend**: Located in `./backend`. Run `cd backend && uvicorn app.main:app --reload` for local python dev (requires venv).
- **Frontend**: Located in `./frontend`. Run `cd frontend && npm run dev`.
- **Admin Frontend**: Located in `./admin_frontend/mantine-analytics-dashboard`. Run `cd admin_frontend/mantine-analytics-dashboard && npm run dev`.

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
