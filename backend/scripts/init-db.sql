-- Initialize HackOps Database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas for multi-tenancy if needed
-- CREATE SCHEMA IF NOT EXISTS tenant_data;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE hackops_dev TO hackops;

-- Create indexes for common queries (will be managed by Alembic later)
-- This is just for initial setup
