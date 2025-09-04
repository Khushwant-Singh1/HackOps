# Tenant Management and Multi-Tenancy Infrastructure

## Overview

Task 4 implements a comprehensive multi-tenant platform management system for HackOps, providing complete tenant isolation, billing foundations, and scalable architecture for hosting multiple organizations on a single platform.

## 🏗️ Architecture

### Core Components

1. **Tenant Service Layer** (`app/services/tenant_service.py`)
   - Tenant CRUD operations
   - User management within tenants
   - Usage tracking and billing
   - Plan management and feature flags

2. **Tenant-Scoped Base Service** (`app/services/base_tenant_service.py`)
   - Base class for all services with automatic tenant isolation
   - Generic CRUD operations with tenant context
   - Permission checking and access validation

3. **Row-Level Security (RLS)** (`app/core/tenant_rls.py`)
   - PostgreSQL RLS policies for database-level isolation
   - Tenant context management
   - System admin bypass functionality

4. **API Endpoints** (`app/api/v1/tenants.py`)
   - RESTful APIs for tenant management
   - User invitation and role management
   - Usage tracking and statistics

5. **Database Utilities** (`app/core/database_utils.py`)
   - Enhanced tenant context management
   - Session isolation and cleanup
   - Performance monitoring

## 🔐 Security Model

### Tenant Isolation Levels

1. **Application Level**
   - Service layer automatically filters by tenant_id
   - Request context includes tenant information
   - API endpoints validate tenant access

2. **Database Level**
   - PostgreSQL Row-Level Security policies
   - Automatic filtering at SQL level
   - Protection against application-level bypasses

3. **Session Level**
   - PostgreSQL session variables for tenant context
   - Automatic context cleanup
   - System admin bypass capabilities

### Access Control

```python
# Tenant roles and their capabilities
TenantRole.OWNER       # Full tenant management
TenantRole.ADMIN       # User management, configuration
TenantRole.MEMBER      # Event creation, team participation
TenantRole.VIEWER      # Read-only access
```

## 📊 Subscription Plans

### Plan Features and Limits

| Plan | Events | Participants | Storage | Admins | Features |
|------|--------|--------------|---------|---------|----------|
| **Free** | 1 | 50 | 1GB | 1 | Basic events, team formation |
| **Starter** | 5 | 200 | 5GB | 3 | + Custom branding, analytics |
| **Professional** | 20 | 1,000 | 25GB | 10 | + Advanced judging, sponsors |
| **Enterprise** | 100 | 5,000 | 100GB | 50 | + SSO, API access, white-label |

### Usage Tracking

```python
# Track usage for specific metrics
await tenant_service.track_usage(
    db=db,
    tenant_id=tenant_id,
    metric="events",
    amount=1
)

# Get usage statistics
stats = await tenant_service.get_usage_stats(db, tenant_id)
```

## 🚀 Implementation Guide

### 1. Database Setup

First, set up Row-Level Security policies:

```bash
# Run the tenant isolation setup script
python scripts/setup_tenant_isolation.py
```

This creates:
- PostgreSQL functions for tenant context
- RLS policies on all tenant-scoped tables
- Database roles for access control

### 2. Tenant Creation

```python
# Create a new tenant
tenant = await tenant_service.create_tenant(
    db=db,
    creator_user_id=user.id,
    name="Acme University",
    slug="acme-university",
    contact_email="admin@acme.edu",
    plan=TenantPlan.PROFESSIONAL.value,
    organization_type="university",
    website_url="https://acme.edu"
)
```

### 3. Tenant-Scoped Services

All services should inherit from `TenantScopedService`:

```python
from app.services.base_tenant_service import TenantScopedService
from app.models.event import Event

class EventService(TenantScopedService[Event]):
    def __init__(self):
        super().__init__(Event)
    
    async def create_event(self, db: Session, tenant_id: UUID, event_data: dict):
        # Automatic tenant isolation
        return await self.create(
            db=db,
            tenant_id=tenant_id,
            obj_data=event_data
        )
```

### 4. API Usage

#### Tenant Management

```bash
# Create tenant
POST /api/v1/tenants/
{
    "name": "Tech Corp",
    "slug": "tech-corp",
    "contact_email": "admin@techcorp.com",
    "plan": "starter"
}

# Get tenant
GET /api/v1/tenants/{tenant_id}

# Update tenant
PUT /api/v1/tenants/{tenant_id}
{
    "name": "Updated Name",
    "plan": "professional"
}
```

#### User Management

```bash
# Add user to tenant
POST /api/v1/tenants/{tenant_id}/users
{
    "user_id": "user-uuid",
    "role": "admin",
    "permissions": {"can_manage_events": true}
}

# Get tenant users
GET /api/v1/tenants/{tenant_id}/users?role=admin
```

#### Usage Tracking

```bash
# Track usage
POST /api/v1/tenants/{tenant_id}/usage
{
    "metric": "events",
    "amount": 1
}

# Get usage stats
GET /api/v1/tenants/{tenant_id}/usage
```

### 5. Tenant Context

#### Method 1: Path Parameter (Admin/Management)
```
/api/v1/tenants/{tenant_id}/events
```

#### Method 2: HTTP Header
```
X-Tenant-ID: tenant-uuid
```

#### Method 3: Subdomain
```
acme-university.hackops.com
```

## 🧪 Testing

### Run Tenant Tests

```bash
# Run all tenant tests
pytest tests/test_tenant_management.py -v

# Run specific test categories
pytest tests/test_tenant_management.py::TestTenantService -v
pytest tests/test_tenant_management.py::TestTenantIsolation -v
```

### Test Categories

1. **Tenant Service Tests**
   - CRUD operations
   - User management
   - Usage tracking

2. **Isolation Tests**
   - RLS policy verification
   - Cross-tenant access prevention
   - Context management

3. **API Tests**
   - Endpoint functionality
   - Authentication and authorization
   - Error handling

4. **Performance Tests**
   - Bulk operations
   - Query optimization
   - Scalability testing

## 🔧 Configuration

### Environment Variables

```bash
# Database settings for multi-tenancy
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_RECYCLE=3600

# Tenant isolation settings
ENABLE_TENANT_ISOLATION=true
SYSTEM_ADMIN_BYPASS=false

# Plan limits (can be overridden per tenant)
FREE_PLAN_EVENTS=1
STARTER_PLAN_EVENTS=5
PROFESSIONAL_PLAN_EVENTS=20
ENTERPRISE_PLAN_EVENTS=100
```

### Feature Flags

```python
# Enable/disable features per plan
features_config = {
    "custom_branding": ["starter", "professional", "enterprise"],
    "sso_integration": ["enterprise"],
    "api_access": ["professional", "enterprise"],
    "white_label": ["enterprise"]
}
```

## 📈 Monitoring and Analytics

### Usage Metrics

Track and monitor:
- Tenant growth and churn
- Feature adoption by plan
- Resource utilization
- Performance metrics

### Health Checks

```python
# Verify tenant isolation
isolation_status = await rls_manager.verify_tenant_isolation(db, tenant_id)

# Check database health
db_health = await db_manager.health_check()
```

## 🚨 Troubleshooting

### Common Issues

1. **RLS Policies Not Working**
   ```bash
   # Check if RLS is enabled
   SELECT schemaname, tablename, rowsecurity 
   FROM pg_tables 
   WHERE rowsecurity = true;
   
   # Verify policies exist
   SELECT * FROM pg_policies 
   WHERE policyname LIKE '%tenant%';
   ```

2. **Tenant Context Not Set**
   ```python
   # Debug tenant context
   current_tenant = db.execute(
       text("SELECT current_setting('app.current_tenant_id', true)")
   ).scalar()
   print(f"Current tenant: {current_tenant}")
   ```

3. **Permission Denied Errors**
   ```python
   # Check system admin context
   is_admin = db.execute(
       text("SELECT current_setting('app.is_system_admin', true)")
   ).scalar()
   print(f"System admin: {is_admin}")
   ```

### Performance Optimization

1. **Database Indexing**
   ```sql
   -- Ensure tenant_id columns are indexed
   CREATE INDEX idx_events_tenant_id ON events(tenant_id);
   CREATE INDEX idx_teams_tenant_id ON teams(tenant_id);
   ```

2. **Query Optimization**
   ```python
   # Use tenant-scoped services for automatic optimization
   service = TenantScopedService(Event)
   events = await service.list_objects(db, tenant_id, filters={"status": "active"})
   ```

## 🔄 Migration Guide

### Existing Data Migration

When implementing multi-tenancy on existing data:

1. **Add tenant_id columns**
   ```sql
   ALTER TABLE events ADD COLUMN tenant_id UUID REFERENCES tenants(id);
   ALTER TABLE teams ADD COLUMN tenant_id UUID REFERENCES tenants(id);
   ```

2. **Migrate existing data**
   ```python
   # Assign default tenant to existing records
   default_tenant = create_default_tenant()
   update_existing_records(default_tenant.id)
   ```

3. **Enable RLS**
   ```bash
   python scripts/setup_tenant_isolation.py
   ```

## 📚 API Reference

### Tenant Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tenants/` | Create tenant |
| GET | `/api/v1/tenants/` | List tenants |
| GET | `/api/v1/tenants/{id}` | Get tenant |
| PUT | `/api/v1/tenants/{id}` | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Delete tenant |

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tenants/{id}/users` | Add user |
| GET | `/api/v1/tenants/{id}/users` | List users |
| PUT | `/api/v1/tenants/{id}/users/{user_id}` | Update user role |
| DELETE | `/api/v1/tenants/{id}/users/{user_id}` | Remove user |

### Usage Tracking

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tenants/{id}/usage` | Track usage |
| GET | `/api/v1/tenants/{id}/usage` | Get usage stats |

## 🎯 Success Criteria

Task 4 is complete when:

✅ **Tenant Creation and Configuration**
- [x] Tenant CRUD operations with validation
- [x] Plan management and feature flags
- [x] Branding and customization support

✅ **Database-Level Isolation**
- [x] PostgreSQL RLS policies implemented
- [x] Tenant context management
- [x] System admin bypass functionality

✅ **Tenant-Scoped Services**
- [x] Base service class with automatic isolation
- [x] Generic CRUD operations
- [x] Permission checking and validation

✅ **Billing and Usage Tracking**
- [x] Usage metrics tracking
- [x] Plan limits enforcement
- [x] Statistics and reporting

✅ **Comprehensive Testing**
- [x] Unit tests for all components
- [x] Integration tests for isolation
- [x] API endpoint testing
- [x] Performance and security tests

## 🔮 Future Enhancements

1. **Advanced Billing**
   - Payment gateway integration
   - Automated billing cycles
   - Usage-based pricing

2. **Enhanced Analytics**
   - Tenant-specific dashboards
   - Usage trend analysis
   - Predictive scaling

3. **Multi-Region Support**
   - Geographic tenant isolation
   - Data residency compliance
   - Performance optimization

4. **Advanced Security**
   - Audit logging per tenant
   - Compliance reporting
   - Data encryption at rest

---

The tenant management and multi-tenancy infrastructure provides a solid foundation for scaling HackOps to support multiple organizations while maintaining complete data isolation and security.
