# Dumacle Backend

FastAPI backend for Dumacle with async I/O, video transcoding, and multi-storage provider support.

## Features

- **Async-First Architecture**: Built with FastAPI for high-performance async I/O operations
- **User Management**: Role-Based Access Control (RBAC) with Superadmin, Admin, and Enduser roles
- **Duma Pods**: Multi-storage plans (S3, Wasabi, Oracle) with capacity management
- **Type Safety**: Pydantic v2 for schema validation and auto-generated OpenAPI docs
- **Multi-Storage Support**: S3, Oracle Cloud Storage, and Wasabi integration
- **Video Transcoding**: FFmpeg-based transcoding with Celery background workers
- **Subscription Management**: Stripe integration for plan management and webhooks
- **Scalable**: Supports horizontal scaling with Gunicorn/Uvicorn workers
- **Testable**: Comprehensive test suite with pytest (unit/integration/e2e)

## Tech Stack

- **Framework**: FastAPI 0.124+
- **Database**: PostgreSQL with SQLAlchemy (async) + Alembic migrations
- **Queue**: Celery + Redis
- **Storage**: Boto3 (S3-compatible: AWS, Oracle, Wasabi)
- **Auth**: JWT (python-jose)
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio, httpx

## Project Structure

```
dumacle-backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config/              # Configuration (settings, database, storage)
│   ├── middleware/          # Custom middleware (auth, quota, rate limiting)
│   ├── routers/             # API routes (auth, plans, files, webhooks)
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic layer
│   ├── repositories/        # Data access layer
│   ├── core/                # Security and dependencies
│   ├── utils/               # Helpers and utilities
│   └── tasks/               # Celery background tasks
├── tests/                   # Test suite
├── alembic/                 # Database migrations
└── scripts/                 # Automation scripts
```

## Setup & Installation

For detailed installation and configuration instructions, please refer to the **[Installation Guide](INSTALLATION.md)**.

For production deployment to a Linux server, see the **[Deployment Guide](DEPLOYMENT.md)**.

The guides cover:
- System Prerequisites
- Local Development Setup (PostgreSQL + Poetry)
- Docker Setup
- Production Deployment (Linux Server)
- Environment Variables
- Troubleshooting

### Quick Start (Local)

1.  **Install dependencies**: `poetry install`
2.  **Configure environment**: `cp .env.example .env` (ensure PostgreSQL URL)
3.  **Run migrations**: `poetry run alembic upgrade head`
4.  **Seed database**: `python scripts/seed.py` (creates default superadmin: `admin@example.com` / `admin123456`)
5.  **Start server**: `poetry run uvicorn src.main:app --reload`

### Development (Legacy/Manual)
## Storage Features

- **Multi-Provider Support**: AWS S3, Wasabi, and Oracle Object Storage.
- **Dynamic Provider Selection**: Configure primary and secondary storage providers per DumaPod.
- **Custom Credentials**:
    - Supports per-Pod custom storage credentials (e.g., specific S3 buckets/keys for a client).
    - Toggle between system default credentials and custom credentials using `use_custom_s3`, `use_custom_wasabi`, `use_custom_oracle` flags.
    - Secure credential management via API.
- **Credential Validation**:
    - Automatically validates connectivity when enabling custom credentials.
    - Prevents enabling `use_custom_*` flags if the associated credentials are invalid or missing.
- **Direct Uploads**: ✅ **Implemented!** Presigned URLs for direct client-to-S3 uploads (2-3x faster, no server bandwidth).

Start the FastAPI server with auto-reload:
```bash
poetry run uvicorn src.main:app --reload --port 8000
```

Or using the virtual environment directly:
```bash
source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

API documentation will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production

Using Gunicorn with Uvicorn workers:
```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

Build and run with Docker Compose:
```bash
docker-compose up --build
```

This will start:
- FastAPI application
- PostgreSQL database
- Redis
- Celery worker

## Running Celery Workers

For background tasks (transcoding, quota resets):
```bash
celery -A src.tasks.celery_app worker --loglevel=info
```

For periodic tasks (e.g., monthly quota resets):
```bash
celery -A src.tasks.celery_app beat --loglevel=info
```

## Testing

Run all tests:
```bash
poetry run pytest
```

Run with coverage:
```bash
poetry run pytest --cov=src --cov-report=html
```

Run specific test types:
```bash
# Unit tests only
poetry run pytest -m unit

# Integration tests
poetry run pytest -m integration

# E2E tests
poetry run pytest -m e2e
```

## Code Quality

Format code with Black:
```bash
poetry run black src tests
```

Lint with Ruff:
```bash
poetry run ruff check src tests
```

Type checking with mypy:
```bash
poetry run mypy src
```

Run all checks (pre-commit hooks):
```bash
poetry run pre-commit run --all-files
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `STRIPE_SECRET_KEY`: Stripe API secret key
- `JWT_SECRET_KEY`: Secret for JWT token generation
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 1440 = 24 hours)
- `STORAGE_PROVIDER`: Storage backend (s3, oracle, wasabi)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `MAX_FILE_SIZE_MB`: Maximum upload size in MB

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Users
- `POST /users` - Create a new user (Admin/Superadmin only)
- `GET /users` - List all users (Admin/Superadmin only)
- `GET /users/me` - Get current user profile
- `GET /users/{user_id}` - Get specific user details
- `PATCH /users/{user_id}` - Update user details

### Duma Pods (Storage Plans)
- `POST /dumapods` - Create a new storage pod (Admin/Superadmin)
- `GET /dumapods` - List all pods (Admin/Superadmin)
- `GET /dumapods/{pod_id}` - Get pod details
- `PATCH /dumapods/{pod_id}` - Update pod
- `DELETE /dumapods/{pod_id}` - Soft delete pod



### Plans
- `GET /plans` - List available subscription plans
- `POST /plans/subscribe` - Subscribe to a plan

### Files

**Direct Upload (Recommended - 2-3x faster)**:
- `POST /files/initiate-upload` - Get presigned URL for direct S3 upload
- `POST /files/confirm-upload/{file_id}` - Confirm upload completion

**Legacy Upload (Backward compatible)**:
- `POST /files/upload` - Upload file through server (slower, uses server bandwidth)

**File Management**:
- `GET /files` - List user's files (includes `upload_status` and `upload_progress`)
- `GET /files/{file_id}` - Get file details (polling this endpoint returns real-time `upload_progress` 0-100)
- `GET /files/{file_id}/download` - Get presigned download URL

### Webhooks
- `POST /webhooks/stripe` - Stripe webhook handler

## Architecture

This project follows a **hexagonal architecture** pattern with clear separation of concerns:

1. **Routers**: Handle HTTP requests/responses
2. **Services**: Business logic and orchestration
3. **Repositories**: Data access abstraction
4. **Core**: Security, dependencies, and shared utilities

This structure ensures:
- **Testability**: Easy to mock dependencies
- **Scalability**: Modular, feature-based organization
- **Maintainability**: Clear boundaries between layers
- **Type Safety**: Full Pydantic validation throughout

## License

[Your License Here]

## Contributing

[Contributing guidelines]

