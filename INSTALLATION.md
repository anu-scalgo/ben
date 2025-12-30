# Installation & Configuration Guide

This document provides detailed instructions for setting up, configuring, and running the Dumacle Backend.

## 1. Prerequisites

Before starting, ensure your system meets the following requirements:

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Python**: Version 3.12 or higher
- **PostgreSQL**: Version 14 or higher
- **Redis**: Version 6 or higher
- **FFmpeg**: Installed and available in PATH (for video transcoding)
- **Poetry**: Python dependency manager

### Installing Prerequisites (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.12 (if not available, use deadsnakes PPA)
sudo apt install python3.12 python3.12-venv python3.12-dev

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Install Redis
sudo apt install redis-server

# Install FFmpeg
sudo apt install ffmpeg

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

## 2. Local Development Setup (Recommended)

Follow these steps to run the application locally with a PostgreSQL database.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd dumacle-backend
```

### Step 2: Database Setup

Create the PostgreSQL user and database.

```bash
# Set password for default 'postgres' user (prompts for input)
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# Create the application database
sudo -u postgres createdb dumacle
```

### Step 3: Install Dependencies

Use Poetry to install project dependencies.

```bash
poetry install
```

### Step 4: Configuration

1.  **Create .env file**:
    Copy the example configuration file.
    ```bash
    cp .env.example .env
    ```

2.  **Edit .env**:
    Ensure the database connection string points to your local PostgreSQL instance:
    ```ini
    # Database
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dumacle

    # Redis
    REDIS_URL=redis://localhost:6379/0
    ```

### Step 5: Database Migrations

Apply the database schema using Alembic.

```bash
poetry run alembic upgrade head
```

### Step 6: Start the Application

Run the development server with hot-reload.

```bash
poetry run uvicorn src.main:app --reload --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000).
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 3. Docker Setup (Alternative)

You can also run the entire stack using Docker Compose.

```bash
# Build and start all services
docker-compose up --build
```

**Note**: If you run into port conflicts (e.g., local Redis on port 6379), modify `docker-compose.yml` to map ports differently (e.g., `"6380:6379"`).

## 4. Configuration Reference

The application is configured via environment variables in the `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection info | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | **CHANGE IN PRODUCTION** |
| `STORAGE_PROVIDER` | `s3`, `oracle`, or `wasabi` | `s3` |
| `AWS_ACCESS_KEY_ID` | AWS Credentials | - |
| `STRIPE_SECRET_KEY` | Stripe API Secret | - |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## 5. Running Background Workers

For video transcoding and periodic tasks, you need to run Celery workers.

**Worker (Process Tasks)**:
```bash
poetry run celery -A src.tasks.celery_app worker --loglevel=info
```

**Beat (Periodic Scheduler)**:
```bash
poetry run celery -A src.tasks.celery_app beat --loglevel=info
```

## 6. Testing

Run the test suite using `pytest`.

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=src --cov-report=html
```

## 7. Troubleshooting

### Database Authentication Failed
If you see `FATAL: password authentication failed for user "postgres"`, ensure you have set the password correctly in **Step 2** or update the `DATABASE_URL` in `.env` with the correct credentials.

### Port Already in Use
If port `8000` is busy:
```bash
# Find the process
lsof -i :8000
# Kill it
kill -9 <PID>
```

### Alembic "InvalidRequestError"
If you see `The asyncio extension requires an async driver...`, ensure you calculate `dependencies` properly and have updated `alembic/env.py` to use `settings.database_url` (async) for online migrations.
