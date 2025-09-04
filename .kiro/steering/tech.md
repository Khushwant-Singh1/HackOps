# Technology Stack

## Backend
- **Framework**: Python FastAPI for high-performance API development
- **ORM**: SQLAlchemy with Alembic for database migrations
- **Validation**: Pydantic for data validation and serialization
- **Background Jobs**: Celery with Redis for job queues
- **WebSockets**: FastAPI WebSocket for real-time features

## Frontend
- **Framework**: Next.js 14+ with React 18+
- **Styling**: Tailwind CSS with custom design system
- **PWA**: Progressive Web App capabilities for offline functionality
- **Real-time**: WebSocket integration for live updates

## Database & Storage
- **Primary DB**: PostgreSQL 15+ with JSONB support
- **Cache/Queue**: Redis for caching, sessions, and job queues
- **Search**: OpenSearch for full-text search and analytics
- **File Storage**: S3-compatible storage with CDN delivery
- **Connection Pooling**: pgbouncer for database connections

## Infrastructure
- **Containers**: Docker with multi-stage builds
- **Orchestration**: Kubernetes for scaling and deployment
- **Proxy**: Nginx as reverse proxy and load balancer
- **Monitoring**: Prometheus + Grafana
- **Error Tracking**: Sentry integration

## Architecture Patterns
- **Design**: Domain-Driven Design with bounded contexts
- **Structure**: Modular monolith (can evolve to microservices)
- **Multi-tenancy**: Row-level security with tenant isolation
- **Real-time**: WebSocket gateway for live features
- **Offline**: Service Workers for offline caching and sync

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Database setup
alembic upgrade head

# Start development servers
uvicorn main:app --reload  # Backend
npm run dev                # Frontend

# Run tests
pytest                     # Backend tests
npm test                   # Frontend tests
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Docker Operations
```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]
```