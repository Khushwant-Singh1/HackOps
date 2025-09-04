"""
Database migration script for setting up tenant isolation with Row-Level Security.

This script creates the necessary PostgreSQL functions, policies, and roles
to enforce tenant data isolation at the database level.

Run this after creating your database schema to enable multi-tenant isolation.
"""

import logging
from sqlalchemy import text, MetaData, inspect
from sqlalchemy.engine import Engine

from app.core.database import engine
from app.core.tenant_rls import rls_manager

logger = logging.getLogger(__name__)


def create_tenant_isolation_functions(engine: Engine) -> None:
    """
    Create PostgreSQL functions for tenant context management.
    
    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Creating tenant isolation functions...")
    
    with engine.connect() as conn:
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
        
        conn.commit()
        logger.info("Tenant isolation functions created successfully")


def create_database_roles(engine: Engine) -> None:
    """
    Create database roles for tenant isolation.
    
    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Creating database roles...")
    
    with engine.connect() as conn:
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
        
        # Grant permissions to roles
        conn.execute(text("""
            -- Permissions for tenant_user role
            GRANT CONNECT ON DATABASE hackops TO tenant_user;
            GRANT USAGE ON SCHEMA public TO tenant_user;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tenant_user;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tenant_user;
            
            -- Permissions for system_admin role
            GRANT ALL PRIVILEGES ON DATABASE hackops TO system_admin;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO system_admin;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO system_admin;
        """))
        
        conn.commit()
        logger.info("Database roles created successfully")


def get_tenant_tables(engine: Engine) -> list[str]:
    """
    Get list of tables that have tenant_id column.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        List of table names that are tenant-scoped
    """
    inspector = inspect(engine)
    tenant_tables = []
    
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        
        if 'tenant_id' in column_names:
            tenant_tables.append(table_name)
    
    logger.info(f"Found {len(tenant_tables)} tenant-scoped tables: {tenant_tables}")
    return tenant_tables


def create_rls_policies(engine: Engine) -> None:
    """
    Create Row-Level Security policies for tenant isolation.
    
    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Creating RLS policies...")
    
    tenant_tables = get_tenant_tables(engine)
    
    with engine.connect() as conn:
        for table_name in tenant_tables:
            logger.info(f"Creating RLS policies for table: {table_name}")
            
            # Enable RLS on the table
            conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
            
            # Force RLS for table owners
            conn.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))
            
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
            
            logger.info(f"RLS policies created for table: {table_name}")
        
        conn.commit()
        logger.info("All RLS policies created successfully")


def verify_rls_setup(engine: Engine) -> dict:
    """
    Verify that RLS setup is working correctly.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        Dictionary with verification results
    """
    logger.info("Verifying RLS setup...")
    
    results = {
        "functions_exist": False,
        "roles_exist": False,
        "policies_exist": False,
        "tables_with_rls": []
    }
    
    with engine.connect() as conn:
        # Check if functions exist
        function_check = conn.execute(text("""
            SELECT COUNT(*) FROM pg_proc 
            WHERE proname IN ('get_current_tenant_id', 'has_tenant_access', 'is_system_admin')
        """)).scalar()
        
        results["functions_exist"] = function_check >= 3
        
        # Check if roles exist
        role_check = conn.execute(text("""
            SELECT COUNT(*) FROM pg_roles 
            WHERE rolname IN ('tenant_user', 'system_admin')
        """)).scalar()
        
        results["roles_exist"] = role_check >= 2
        
        # Check tables with RLS enabled
        rls_tables = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN (
                SELECT tablename FROM pg_policies 
                WHERE policyname LIKE '%tenant%'
            )
        """)).fetchall()
        
        results["tables_with_rls"] = [table[0] for table in rls_tables]
        results["policies_exist"] = len(results["tables_with_rls"]) > 0
    
    logger.info(f"RLS verification results: {results}")
    return results


def setup_tenant_isolation():
    """
    Main function to set up complete tenant isolation.
    
    This function orchestrates the entire setup process:
    1. Create isolation functions
    2. Create database roles
    3. Set up RLS policies
    4. Verify setup
    """
    logger.info("Starting tenant isolation setup...")
    
    try:
        # Step 1: Create functions
        create_tenant_isolation_functions(engine)
        
        # Step 2: Create roles
        create_database_roles(engine)
        
        # Step 3: Set up RLS policies
        create_rls_policies(engine)
        
        # Step 4: Verify setup
        verification_results = verify_rls_setup(engine)
        
        if all([
            verification_results["functions_exist"],
            verification_results["roles_exist"],
            verification_results["policies_exist"]
        ]):
            logger.info("✅ Tenant isolation setup completed successfully!")
            logger.info(f"✅ RLS enabled on {len(verification_results['tables_with_rls'])} tables")
            return True
        else:
            logger.error("❌ Tenant isolation setup incomplete!")
            logger.error(f"Functions exist: {verification_results['functions_exist']}")
            logger.error(f"Roles exist: {verification_results['roles_exist']}")
            logger.error(f"Policies exist: {verification_results['policies_exist']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to set up tenant isolation: {e}")
        return False


def tear_down_tenant_isolation():
    """
    Remove tenant isolation setup (for testing/development).
    
    WARNING: This will remove all RLS policies and functions!
    Only use in development environments.
    """
    logger.warning("Tearing down tenant isolation setup...")
    
    with engine.connect() as conn:
        # Get tenant tables
        tenant_tables = get_tenant_tables(engine)
        
        # Remove RLS policies
        for table_name in tenant_tables:
            conn.execute(text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"))
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table_name};"))
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_insert_policy ON {table_name};"))
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_update_policy ON {table_name};"))
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_delete_policy ON {table_name};"))
        
        # Drop functions
        conn.execute(text("DROP FUNCTION IF EXISTS get_current_tenant_id();"))
        conn.execute(text("DROP FUNCTION IF EXISTS has_tenant_access(UUID);"))
        conn.execute(text("DROP FUNCTION IF EXISTS is_system_admin();"))
        
        # Note: We don't drop roles as they might be in use
        
        conn.commit()
        logger.warning("Tenant isolation setup removed")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run setup
    success = setup_tenant_isolation()
    
    if success:
        print("🎉 Tenant isolation setup completed successfully!")
        print("Your database is now configured for multi-tenant isolation.")
    else:
        print("💥 Tenant isolation setup failed!")
        print("Please check the logs for more details.")
        exit(1)
