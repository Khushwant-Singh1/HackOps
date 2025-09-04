# HackOps Backend

HackOps is an end-to-end hackathon organizing and execution platform built with FastAPI, PostgreSQL, and Redis.

## Features

- 🏗️ **Multi-tenant Architecture**: Support for multiple organizations and events
- 🔐 **Authentication & Authorization**: JWT-based auth with OAuth integration
- 📊 **Real-time Features**: WebSocket support for live updates
- 🚀 **High Performance**: FastAPI with async/await support
- 🐳 **Containerized**: Docker and Docker Compose ready
- 📝 **Auto-generated API Docs**: OpenAPI/Swagger documentation
- 🧪 **Comprehensive Testing**: Unit and integration tests
- 📈 **Background Jobs**: Celery for async task processing

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HackOps/backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start development services with Docker**
   ```bash
   ./scripts/dev.sh docker-dev
   ```

6. **Run database migrations**
   ```bash
   ./scripts/dev.sh setup-db
   ```

7. **Start development server**
   ```bash
   ./scripts/dev.sh dev
   ```

The API will be available at:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Using Docker Compose

For a complete development environment with all services:

```bash
# Start all services (PostgreSQL, Redis, API, Celery)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Services

When using `docker-compose.dev.yml`, the following services are available:

- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **PgAdmin**: http://localhost:5050 (admin@hackops.com / admin123)
- **Redis Commander**: http://localhost:8081

## Development Scripts

The `scripts/dev.sh` utility provides common development tasks:

```bash
# Install dependencies
./scripts/dev.sh install

# Install development dependencies
./scripts/dev.sh install-dev

# Start development server
./scripts/dev.sh dev

# Start Docker development environment
./scripts/dev.sh docker-dev

# Stop Docker services
./scripts/dev.sh docker-stop

# Run tests
./scripts/dev.sh test

# Format code
./scripts/dev.sh format

# Lint code
./scripts/dev.sh lint

# Create database migration
./scripts/dev.sh migration "Add user table"

# Run migrations
./scripts/dev.sh migrate

# Rollback last migration
./scripts/dev.sh rollback

# Clean up cache files
./scripts/dev.sh cleanup
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/           # API route handlers
│   ├── core/             # Core configuration and utilities
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic layer
│   └── workers/          # Celery background tasks
├── alembic/              # Database migrations
├── scripts/              # Development and deployment scripts
├── tests/                # Test files
├── docker-compose.yml    # Production Docker Compose
├── docker-compose.dev.yml # Development Docker Compose
├── Dockerfile            # Docker image definition
└── requirements.txt      # Python dependencies
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Application
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hackops_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GITHUB_CLIENT_ID=your-github-client-id
```

## API Documentation

Once the server is running, visit:

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run tests with specific markers
pytest -m "unit"
pytest -m "integration"
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add user table"

# Run migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# View migration history
alembic history
```

## Code Quality

The project uses several tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing

```bash
# Format code
black .
isort .

# Check code style
flake8 .

# Type checking
mypy app/

# Run all quality checks
./scripts/dev.sh lint
```

## Background Tasks

The application uses Celery for background task processing:

```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info

# Monitor tasks
celery -A app.core.celery_app flower
```

## Production Deployment

For production deployment:

1. Set production environment variables
2. Use `docker-compose.yml` for production services
3. Configure reverse proxy (Nginx)
4. Set up monitoring and logging
5. Configure SSL/TLS certificates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License.
