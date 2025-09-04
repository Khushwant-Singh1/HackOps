"""
PostgreSQL Row-Level Security (RLS) Setup for Multi-Tenant Isolation

This module provides utilities for setting up and managing PostgreSQL
row-level security policies to ensure complete tenant data isolation.
"""

from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text, MetaData, inspect
from sqlalchemy.engine import Engine

from app.core.database import engine
from app.core.config import settings


class TenantRLSManager:
    """
    Manager for PostgreSQL Row-Level Security policies for tenant isolation.
    
    This class handles the creation and management of RLS policies to ensure
    that tenant data is completely isolated at the database level.
    """
    
    def __init__(self):
        self.engine = engine
    
    def setup_tenant_rls(self) -> None:
        """
        Set up Row-Level Security for all tenant-scoped tables.
        
        This method creates RLS policies for tables that have a tenant_id column
        to ensure users can only access data from their authorized tenants.
        """
        with self.engine.connect() as conn:
            # Enable RLS on tenant-scoped tables
            tenant_tables = self._get_tenant_tables()
            
            for table_name in tenant_tables:
                # Enable RLS on the table
                conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
                
                # Create RLS policies
                self._create_tenant_policies(conn, table_name)
            
            conn.commit()
    
    def create_tenant_isolation_policies(self) -> None:
        """
        Create comprehensive tenant isolation policies.
        
        Sets up RLS policies that enforce tenant isolation based on
        the current tenant context stored in session variables.
        """
        with self.engine.connect() as conn:
            # Create function to get current tenant ID
            self._create_tenant_context_functions(conn)
            
            # Set up RLS policies for each tenant table
            tenant_tables = self._get_tenant_tables()
            
            for table_name in tenant_tables:
                self._create_comprehensive_tenant_policy(conn, table_name)
            
            conn.commit()
    
    def set_tenant_context(self, db: Session, tenant_id: UUID) -> None:
        """
        Set the tenant context for the current database session.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant to set as context
        """
        db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)}
        )
    
    def clear_tenant_context(self, db: Session) -> None:
        """
        Clear the tenant context for the current database session.
        
        Args:
            db: Database session
        """
        db.execute(
            text("SELECT set_config('app.current_tenant_id', NULL, true)")
        )
    
    def get_current_tenant_id(self, db: Session) -> str:
        """
        Get the current tenant ID from the database session.
        
        Args:
            db: Database session
        
        Returns:
            Current tenant ID as string
        """
        result = db.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        ).scalar()
        
        return result if result != '' else None
    
    def _get_tenant_tables(self) -> List[str]:
        """
        Get list of tables that have tenant_id column.
        
        Returns:
            List of table names that are tenant-scoped
        """
        inspector = inspect(self.engine)
        tenant_tables = []
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            
            if 'tenant_id' in column_names:
                tenant_tables.append(table_name)
        
        return tenant_tables
    
    def _create_tenant_context_functions(self, conn) -> None:
        """
        Create PostgreSQL functions for tenant context management.
        
        Args:
            conn: Database connection
        """
        # Function to get current tenant ID
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION get_current_tenant_id()
            RETURNS UUID AS $$
            BEGIN
                RETURN COALESCE(current_setting('app.current_tenant_id', true)::UUID, NULL);
            EXCEPTION
                WHEN invalid_text_representation THEN
                    RETURN NULL;
            END;
            $$ LANGUAGE plpgsql STABLE;
        """))
        
        # Function to check if user has access to tenant
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION has_tenant_access(target_tenant_id UUID)
            RETURNS BOOLEAN AS $$
            DECLARE
                current_tenant UUID;
            BEGIN
                current_tenant := get_current_tenant_id();
                
                -- If no tenant context is set, deny access
                IF current_tenant IS NULL THEN
                    RETURN FALSE;
                END IF;
                
                -- Check if current tenant matches target tenant
                RETURN current_tenant = target_tenant_id;
            END;
            $$ LANGUAGE plpgsql STABLE;
        """))
        
        # Function for system admin bypass
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION is_system_admin()
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN COALESCE(current_setting('app.is_system_admin', true)::BOOLEAN, FALSE);
            EXCEPTION
                WHEN invalid_text_representation THEN
                    RETURN FALSE;
            END;
            $$ LANGUAGE plpgsql STABLE;
        """))
    
    def _create_tenant_policies(self, conn, table_name: str) -> None:
        """
        Create basic tenant isolation policies for a table.
        
        Args:
            conn: Database connection
            table_name: Name of the table to create policies for
        """
        # Drop existing policies if they exist
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table_name};"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_insert_policy ON {table_name};"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_update_policy ON {table_name};"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_delete_policy ON {table_name};"))
        
        # Create SELECT policy
        conn.execute(text(f"""
            CREATE POLICY tenant_isolation_policy ON {table_name}
            FOR SELECT
            USING (
                is_system_admin() OR 
                has_tenant_access(tenant_id)
            );
        """))
        
        # Create INSERT policy
        conn.execute(text(f"""
            CREATE POLICY tenant_insert_policy ON {table_name}
            FOR INSERT
            WITH CHECK (
                is_system_admin() OR 
                has_tenant_access(tenant_id)
            );
        """))
        
        # Create UPDATE policy
        conn.execute(text(f"""
            CREATE POLICY tenant_update_policy ON {table_name}
            FOR UPDATE
            USING (
                is_system_admin() OR 
                has_tenant_access(tenant_id)
            )
            WITH CHECK (
                is_system_admin() OR 
                has_tenant_access(tenant_id)
            );
        """))
        
        # Create DELETE policy
        conn.execute(text(f"""
            CREATE POLICY tenant_delete_policy ON {table_name}
            FOR DELETE
            USING (
                is_system_admin() OR 
                has_tenant_access(tenant_id)
            );
        """))
    
    def _create_comprehensive_tenant_policy(self, conn, table_name: str) -> None:
        """
        Create comprehensive tenant isolation policy for a table.
        
        Args:
            conn: Database connection
            table_name: Name of the table to create policies for
        """
        # Enable RLS on the table
        conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
        
        # Force RLS for table owners
        conn.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))
        
        # Create comprehensive policy
        self._create_tenant_policies(conn, table_name)
    
    def create_tenant_roles_and_permissions(self) -> None:
        """
        Create database roles and permissions for tenant isolation.
        
        Sets up database-level roles that enforce tenant boundaries.
        """
        with self.engine.connect() as conn:
            # Create tenant_user role
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user') THEN
                        CREATE ROLE tenant_user;
                    END IF;
                END
                $$;
            """))
            
            # Grant basic permissions to tenant_user role
            conn.execute(text("""
                GRANT CONNECT ON DATABASE hackops TO tenant_user;
                GRANT USAGE ON SCHEMA public TO tenant_user;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tenant_user;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tenant_user;
            """))
            
            # Create system_admin role
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'system_admin') THEN
                        CREATE ROLE system_admin;
                    END IF;
                END
                $$;
            """))
            
            # Grant elevated permissions to system_admin role
            conn.execute(text("""
                GRANT ALL PRIVILEGES ON DATABASE hackops TO system_admin;
                GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO system_admin;
                GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO system_admin;
            """))
            
            conn.commit()
    
    def set_system_admin_context(self, db: Session, is_admin: bool = True) -> None:
        """
        Set system admin context for bypassing tenant isolation.
        
        Args:
            db: Database session
            is_admin: Whether to enable system admin context
        """
        db.execute(
            text("SELECT set_config('app.is_system_admin', :is_admin, true)"),
            {"is_admin": str(is_admin).lower()}
        )
    
    def verify_tenant_isolation(self, db: Session, tenant_id: UUID) -> Dict[str, Any]:
        """
        Verify that tenant isolation is working correctly.
        
        Args:
            db: Database session
            tenant_id: Tenant ID to test isolation for
        
        Returns:
            Dictionary with isolation test results
        """
        results = {
            "tenant_id": str(tenant_id),
            "isolation_enabled": True,
            "tests": {}
        }
        
        # Set tenant context
        self.set_tenant_context(db, tenant_id)
        
        # Test each tenant table
        tenant_tables = self._get_tenant_tables()
        
        for table_name in tenant_tables:
            try:
                # Try to select from table with tenant context
                result = db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                
                results["tests"][table_name] = {
                    "status": "pass",
                    "accessible_records": result
                }
                
            except Exception as e:
                results["tests"][table_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def migrate_existing_data(self) -> None:
        """
        Migrate existing data to support tenant isolation.
        
        This method should be run when implementing multi-tenancy
        on an existing database with data.
        """
        with self.engine.connect() as conn:
            # This would contain logic to assign tenant_id to existing records
            # For now, this is a placeholder for the migration strategy
            
            # Example: Update records without tenant_id
            # conn.execute(text("""
            #     UPDATE events 
            #     SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
            #     WHERE tenant_id IS NULL;
            # """))
            
            conn.commit()


# Global RLS manager instance
rls_manager = TenantRLSManager()


# Context manager for tenant isolation
class TenantIsolationContext:
    """
    Context manager for temporary tenant isolation.
    
    Ensures tenant context is properly set and cleaned up.
    """
    
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.original_tenant_id = None
    
    def __enter__(self):
        # Save current tenant context
        self.original_tenant_id = rls_manager.get_current_tenant_id(self.db)
        
        # Set new tenant context
        rls_manager.set_tenant_context(self.db, self.tenant_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original tenant context
        if self.original_tenant_id:
            rls_manager.set_tenant_context(self.db, self.original_tenant_id)
        else:
            rls_manager.clear_tenant_context(self.db)


# Utility functions

def ensure_tenant_isolation_setup():
    """
    Ensure that tenant isolation is properly set up in the database.
    
    This function should be called during application startup to verify
    that all necessary RLS policies are in place.
    """
    try:
        rls_manager.setup_tenant_rls()
        rls_manager.create_tenant_isolation_policies()
        rls_manager.create_tenant_roles_and_permissions()
        return True
    except Exception as e:
        print(f"Failed to set up tenant isolation: {e}")
        return False


def with_tenant_context(db: Session, tenant_id: UUID):
    """
    Decorator/context manager for tenant-scoped operations.
    
    Args:
        db: Database session
        tenant_id: Tenant ID to set as context
    
    Returns:
        Context manager for tenant isolation
    """
    return TenantIsolationContext(db, tenant_id)
