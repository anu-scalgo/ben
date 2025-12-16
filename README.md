# Dumacle Backend

FastAPI backend for Dumacle with async I/O, video transcoding, and multi-storage provider support.

## Features

- **Async-First Architecture**: Built with FastAPI for high-performance async I/O operations
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

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- FFmpeg (for transcoding)
- Poetry (recommended) or pip

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd /home/scalgo/Desktop/ben
   ```

2. **Install dependencies** (using Poetry):
   ```bash
   poetry install
   ```

   Or using pip:
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize Alembic** (if not already done):
   ```bash
   alembic init alembic
   alembic revision --autogenerate -m "init models"
   alembic upgrade head
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Seed initial data** (optional):
   ```bash
   python scripts/seed.py
   ```

## Running the Application

### Development

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
- `STORAGE_PROVIDER`: Storage backend (s3, oracle, wasabi)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `MAX_FILE_SIZE_MB`: Maximum upload size in MB

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Plans
- `GET /plans` - List available subscription plans
- `POST /plans/subscribe` - Subscribe to a plan

### Files
- `POST /files/upload` - Upload file (supports streaming)
- `GET /files` - List user's files
- `GET /files/{file_id}` - Get file details
- `GET /files/{file_id}/download` - Download file

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

