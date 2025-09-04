# Project Structure

## Root Directory Organization
```
hackops/
├── backend/                 # FastAPI backend application
├── frontend/               # Next.js frontend application
├── shared/                 # Shared types and utilities
├── infrastructure/         # Kubernetes, Docker, Terraform configs
├── docs/                   # Documentation and API specs
└── scripts/               # Build and deployment scripts
```

## Backend Structure (FastAPI)
```
backend/
├── app/
│   ├── core/              # Core configuration and utilities
│   │   ├── config.py      # Environment configuration
│   │   ├── security.py    # Authentication and authorization
│   │   └── database.py    # Database connection and session
│   ├── models/            # SQLAlchemy database models
│   │   ├── user.py
│   │   ├── event.py
│   │   ├── team.py
│   │   └── submission.py
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # Business logic layer
│   │   ├── auth_service.py
│   │   ├── event_service.py
│   │   ├── team_service.py
│   │   └── judging_service.py
│   ├── api/               # API route handlers
│   │   ├── v1/            # API version 1
│   │   │   ├── auth.py
│   │   │   ├── events.py
│   │   │   ├── teams.py
│   │   │   └── submissions.py
│   │   └── deps.py        # Dependency injection
│   ├── workers/           # Celery background tasks
│   └── tests/             # Test files mirroring app structure
├── alembic/               # Database migrations
├── requirements.txt       # Python dependencies
└── main.py               # FastAPI application entry point
```

## Frontend Structure (Next.js)
```
frontend/
├── src/
│   ├── app/               # Next.js 14+ app router
│   │   ├── (auth)/        # Authentication routes
│   │   ├── dashboard/     # Dashboard pages
│   │   ├── events/        # Event management pages
│   │   └── layout.tsx     # Root layout
│   ├── components/        # Reusable UI components
│   │   ├── ui/            # Base UI components
│   │   ├── forms/         # Form components
│   │   └── charts/        # Data visualization
│   ├── lib/               # Utilities and configurations
│   │   ├── api.ts         # API client
│   │   ├── auth.ts        # Authentication utilities
│   │   └── utils.ts       # General utilities
│   ├── hooks/             # Custom React hooks
│   ├── stores/            # State management (Zustand/Redux)
│   └── types/             # TypeScript type definitions
├── public/                # Static assets
├── package.json          # Node.js dependencies
└── next.config.js        # Next.js configuration
```

## Key Architectural Principles

### Service Layer Pattern
- Business logic isolated in service classes
- Controllers handle HTTP concerns only
- Services are testable and reusable

### Repository Pattern
- Data access abstracted through repositories
- Easy to mock for testing
- Database-agnostic business logic

### Multi-Tenant Architecture
- All models include `tenant_id` for isolation
- Row-level security enforced at database level
- Tenant context passed through request lifecycle

### API Versioning
- Version-specific route modules (`/api/v1/`)
- Backward compatibility maintained
- Clear deprecation strategy

## File Naming Conventions

### Backend (Python)
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Frontend (TypeScript)
- **Components**: `PascalCase.tsx`
- **Utilities**: `camelCase.ts`
- **Types**: `PascalCase` interfaces
- **Hooks**: `use` prefix + `camelCase`

## Database Conventions

### Table Naming
- Plural nouns: `users`, `events`, `teams`
- Junction tables: `team_members`, `event_sponsors`

### Column Naming
- `snake_case` for all columns
- Foreign keys: `{table}_id` (e.g., `user_id`)
- Timestamps: `created_at`, `updated_at`
- Soft deletes: `deleted_at`

### Index Naming
- `idx_{table}_{columns}` for regular indexes
- `uniq_{table}_{columns}` for unique indexes