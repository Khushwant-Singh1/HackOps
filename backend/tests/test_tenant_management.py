"""
Test suite for Tenant Management and Multi-Tenancy Infrastructure

This comprehensive test suite covers:
- Tenant creation and configuration management
- Tenant user management and role-based access
- Usage tracking and billing foundations
- Database-level tenant isolation with row-level security
- Tenant-scoped service operations
- Multi-tenant data security and isolation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import uuid4, UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from main import app
from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant, TenantUser, TenantStatus, TenantPlan
from app.services.tenant_service import tenant_service
from app.services.base_tenant_service import TenantScopedService
from app.core.tenant_rls import rls_manager, TenantIsolationContext
from app.core.database_utils import tenant_manager as db_tenant_manager
from tests.conftest import TestData, create_test_user, create_test_tenant


class TestTenantService:
    """Test suite for tenant service operations."""
    
    def test_create_tenant_success(self, db: Session, test_user: User):
        """Test successful tenant creation."""
        # Create tenant
        tenant_data = {
            "name": "Test University",
            "slug": "test-university",
            "contact_email": "admin@test-university.edu",
            "plan": TenantPlan.STARTER.value,
            "organization_type": "university",
            "website_url": "https://test-university.edu"
        }
        
        tenant = asyncio.run(tenant_service.create_tenant(
            db=db,
            creator_user_id=test_user.id,
            **tenant_data
        ))
        
        # Verify tenant creation
        assert tenant.name == tenant_data["name"]
        assert tenant.slug == tenant_data["slug"]
        assert tenant.contact_email == tenant_data["contact_email"]
        assert tenant.plan == tenant_data["plan"]
        assert tenant.status == TenantStatus.ACTIVE.value
        
        # Verify plan limits are set
        assert tenant.max_events == 5  # Starter plan limit
        assert tenant.max_participants_per_event == 200
        assert tenant.max_storage_gb == 5
        assert tenant.max_admins == 3
        
        # Verify features are enabled
        expected_features = [
            "basic_events", "team_formation", "basic_submissions",
            "custom_branding", "basic_analytics"
        ]
        for feature in expected_features:
            assert feature in tenant.features_enabled
        
        # Verify creator is added as owner
        tenant_users = asyncio.run(tenant_service.get_tenant_users(
            db=db, tenant_id=tenant.id
        ))
        
        assert len(tenant_users) == 1
        assert tenant_users[0].user_id == test_user.id
        assert tenant_users[0].role == "owner"
        assert tenant_users[0].is_active is True
    
    def test_create_tenant_duplicate_slug(self, db: Session, test_user: User):
        """Test tenant creation with duplicate slug fails."""
        # Create first tenant
        asyncio.run(tenant_service.create_tenant(
            db=db,
            creator_user_id=test_user.id,
            name="Test Tenant 1",
            slug="test-tenant",
            contact_email="admin1@test.com"
        ))
        
        # Try to create second tenant with same slug
        with pytest.raises(Exception):  # Should raise HTTPException
            asyncio.run(tenant_service.create_tenant(
                db=db,
                creator_user_id=test_user.id,
                name="Test Tenant 2",
                slug="test-tenant",
                contact_email="admin2@test.com"
            ))
    
    def test_get_tenant_by_id(self, db: Session, test_tenant: Tenant):
        """Test getting tenant by ID."""
        tenant = asyncio.run(tenant_service.get_tenant(db, test_tenant.id))
        
        assert tenant is not None
        assert tenant.id == test_tenant.id
        assert tenant.name == test_tenant.name
        assert tenant.slug == test_tenant.slug
    
    def test_get_tenant_by_slug(self, db: Session, test_tenant: Tenant):
        """Test getting tenant by slug."""
        tenant = asyncio.run(tenant_service.get_tenant_by_slug(db, test_tenant.slug))
        
        assert tenant is not None
        assert tenant.id == test_tenant.id
        assert tenant.slug == test_tenant.slug
    
    def test_update_tenant(self, db: Session, test_tenant: Tenant):
        """Test updating tenant configuration."""
        update_data = {
            "name": "Updated Tenant Name",
            "contact_email": "new-admin@test.com",
            "plan": TenantPlan.PROFESSIONAL.value,
            "settings": {"theme": "dark", "notifications": True},
            "branding_config": {"primary_color": "#FF5733"}
        }
        
        updated_tenant = asyncio.run(tenant_service.update_tenant(
            db=db,
            tenant_id=test_tenant.id,
            update_data=update_data
        ))
        
        # Verify updates
        assert updated_tenant.name == update_data["name"]
        assert updated_tenant.contact_email == update_data["contact_email"]
        assert updated_tenant.plan == update_data["plan"]
        
        # Verify plan limits updated for Professional plan
        assert updated_tenant.max_events == 20
        assert updated_tenant.max_participants_per_event == 1000
        
        # Verify settings and branding config merged
        assert updated_tenant.settings["theme"] == "dark"
        assert updated_tenant.branding_config["primary_color"] == "#FF5733"
    
    def test_delete_tenant(self, db: Session, test_tenant: Tenant):
        """Test soft deleting a tenant."""
        success = asyncio.run(tenant_service.delete_tenant(db, test_tenant.id))
        
        assert success is True
        
        # Verify tenant is soft deleted
        deleted_tenant = asyncio.run(tenant_service.get_tenant(db, test_tenant.id))
        assert deleted_tenant is None  # Should not be found due to soft delete filter
        
        # Verify tenant exists but is marked deleted
        actual_tenant = db.query(Tenant).filter(Tenant.id == test_tenant.id).first()
        assert actual_tenant.is_deleted is True
        assert actual_tenant.status == TenantStatus.SUSPENDED.value
        assert actual_tenant.deleted_at is not None


class TestTenantUserManagement:
    """Test suite for tenant user management."""
    
    def test_add_tenant_user(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test adding a user to a tenant."""
        # Create additional user
        new_user = create_test_user(db, email="newuser@test.com")
        
        tenant_user = asyncio.run(tenant_service.add_tenant_user(
            db=db,
            tenant_id=test_tenant.id,
            user_id=new_user.id,
            role="admin",
            invited_by_user_id=test_user.id,
            permissions={"can_manage_events": True}
        ))
        
        # Verify tenant user creation
        assert tenant_user.tenant_id == test_tenant.id
        assert tenant_user.user_id == new_user.id
        assert tenant_user.role == "admin"
        assert tenant_user.is_active is True
        assert tenant_user.invited_by_id == test_user.id
        assert tenant_user.permissions["can_manage_events"] is True
    
    def test_add_duplicate_tenant_user(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test adding duplicate user to tenant fails."""
        # Try to add the same user again (test_user is already owner)
        with pytest.raises(Exception):  # Should raise HTTPException
            asyncio.run(tenant_service.add_tenant_user(
                db=db,
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                role="member"
            ))
    
    def test_update_tenant_user_role(self, db: Session, test_tenant: Tenant):
        """Test updating a tenant user's role."""
        # Create user and add to tenant
        user = create_test_user(db, email="member@test.com")
        tenant_user = asyncio.run(tenant_service.add_tenant_user(
            db=db,
            tenant_id=test_tenant.id,
            user_id=user.id,
            role="member"
        ))
        
        # Update role to admin
        updated_tenant_user = asyncio.run(tenant_service.update_tenant_user_role(
            db=db,
            tenant_id=test_tenant.id,
            user_id=user.id,
            new_role="admin",
            permissions={"can_manage_teams": True}
        ))
        
        # Verify role update
        assert updated_tenant_user.role == "admin"
        assert updated_tenant_user.permissions["can_manage_teams"] is True
    
    def test_remove_tenant_user(self, db: Session, test_tenant: Tenant):
        """Test removing a user from a tenant."""
        # Create user and add to tenant
        user = create_test_user(db, email="temp@test.com")
        asyncio.run(tenant_service.add_tenant_user(
            db=db,
            tenant_id=test_tenant.id,
            user_id=user.id,
            role="member"
        ))
        
        # Remove user from tenant
        success = asyncio.run(tenant_service.remove_tenant_user(
            db=db,
            tenant_id=test_tenant.id,
            user_id=user.id
        ))
        
        assert success is True
        
        # Verify user is removed
        tenant_users = asyncio.run(tenant_service.get_tenant_users(
            db=db, tenant_id=test_tenant.id
        ))
        
        user_found = any(tu.user_id == user.id for tu in tenant_users)
        assert user_found is False
    
    def test_get_tenant_users_with_filters(self, db: Session, test_tenant: Tenant):
        """Test getting tenant users with various filters."""
        # Create users with different roles
        admin_user = create_test_user(db, email="admin@test.com")
        member_user = create_test_user(db, email="member@test.com")
        viewer_user = create_test_user(db, email="viewer@test.com")
        
        # Add users to tenant
        asyncio.run(tenant_service.add_tenant_user(
            db=db, tenant_id=test_tenant.id, user_id=admin_user.id, role="admin"
        ))
        asyncio.run(tenant_service.add_tenant_user(
            db=db, tenant_id=test_tenant.id, user_id=member_user.id, role="member"
        ))
        asyncio.run(tenant_service.add_tenant_user(
            db=db, tenant_id=test_tenant.id, user_id=viewer_user.id, role="viewer"
        ))
        
        # Test filter by role
        admin_users = asyncio.run(tenant_service.get_tenant_users(
            db=db, tenant_id=test_tenant.id, role_filter="admin"
        ))
        assert len(admin_users) == 1
        assert admin_users[0].role == "admin"
        
        # Test get all active users
        all_users = asyncio.run(tenant_service.get_tenant_users(
            db=db, tenant_id=test_tenant.id, active_only=True
        ))
        assert len(all_users) == 4  # owner + 3 added users


class TestUsageTrackingAndBilling:
    """Test suite for usage tracking and billing functionality."""
    
    def test_track_usage_success(self, db: Session, test_tenant: Tenant):
        """Test successful usage tracking."""
        # Track event creation
        success = asyncio.run(tenant_service.track_usage(
            db=db,
            tenant_id=test_tenant.id,
            metric="events",
            amount=1
        ))
        
        assert success is True
        
        # Verify usage was tracked
        updated_tenant = asyncio.run(tenant_service.get_tenant(db, test_tenant.id))
        assert updated_tenant.current_events == 1
    
    def test_track_usage_exceeds_limit(self, db: Session, test_tenant: Tenant):
        """Test usage tracking that exceeds limits."""
        # Set current usage near limit
        test_tenant.current_events = test_tenant.max_events
        db.commit()
        
        # Try to track additional usage
        with pytest.raises(Exception):  # Should raise HTTPException
            asyncio.run(tenant_service.track_usage(
                db=db,
                tenant_id=test_tenant.id,
                metric="events",
                amount=1
            ))
    
    def test_get_usage_stats(self, db: Session, test_tenant: Tenant):
        """Test getting usage statistics."""
        # Set some usage data
        test_tenant.current_events = 2
        test_tenant.current_participants = 50
        test_tenant.current_storage_gb = 1.5
        db.commit()
        
        stats = asyncio.run(tenant_service.get_usage_stats(db, test_tenant.id))
        
        # Verify stats structure
        assert stats["plan"] == test_tenant.plan
        assert stats["status"] == test_tenant.status
        
        # Verify usage data
        assert stats["usage"]["events"]["current"] == 2
        assert stats["usage"]["events"]["max"] == test_tenant.max_events
        assert stats["usage"]["events"]["percentage"] == test_tenant.get_usage_percentage("events")
        
        assert stats["usage"]["participants"]["current"] == 50
        assert stats["usage"]["storage"]["current"] == 1.5
        
        # Verify features and subscription info
        assert "features_enabled" in stats
        assert isinstance(stats["features_enabled"], list)


class TestTenantIsolation:
    """Test suite for tenant data isolation and row-level security."""
    
    def test_rls_setup(self, db: Session):
        """Test that row-level security is properly set up."""
        # This would test the actual RLS setup
        # For now, we'll test the context management
        tenant_id = uuid4()
        
        # Test setting tenant context
        db_tenant_manager.set_tenant_context(db, tenant_id)
        
        # Verify context is set
        current_tenant = db_tenant_manager.get_db_tenant_context(db)
        assert current_tenant == str(tenant_id)
        
        # Test clearing context
        db_tenant_manager.clear_tenant_context(db)
        current_tenant = db_tenant_manager.get_db_tenant_context(db)
        assert current_tenant is None
    
    def test_tenant_isolation_context_manager(self, db: Session):
        """Test tenant isolation context manager."""
        tenant_id = uuid4()
        
        # Test context manager
        with TenantIsolationContext(db, tenant_id):
            current_tenant = rls_manager.get_current_tenant_id(db)
            assert current_tenant == str(tenant_id)
        
        # Verify context is cleared after exit
        current_tenant = rls_manager.get_current_tenant_id(db)
        assert current_tenant is None
    
    def test_system_admin_context(self, db: Session):
        """Test system admin context for bypassing isolation."""
        # Set system admin context
        rls_manager.set_system_admin_context(db, True)
        
        # Verify admin context is set
        result = db.execute(
            text("SELECT current_setting('app.is_system_admin', true)")
        ).scalar()
        assert result == "true"
        
        # Clear admin context
        rls_manager.set_system_admin_context(db, False)
        result = db.execute(
            text("SELECT current_setting('app.is_system_admin', true)")
        ).scalar()
        assert result == "false"


class TestTenantScopedService:
    """Test suite for tenant-scoped service base class."""
    
    def test_tenant_scoped_crud_operations(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test CRUD operations with tenant scoping."""
        # Create a test service using the tenant model
        tenant_scoped_service = TenantScopedService(Tenant)
        
        # Test create with tenant context
        tenant_data = {
            "name": "Scoped Test Tenant",
            "slug": "scoped-test",
            "contact_email": "scoped@test.com",
            "plan": TenantPlan.FREE.value,
            "status": TenantStatus.ACTIVE.value
        }
        
        created_tenant = asyncio.run(tenant_scoped_service.create(
            db=db,
            tenant_id=test_tenant.id,
            obj_data=tenant_data,
            created_by_id=test_user.id
        ))
        
        assert created_tenant.name == tenant_data["name"]
        
        # Test get by ID with tenant context
        retrieved_tenant = asyncio.run(tenant_scoped_service.get_by_id(
            db=db,
            tenant_id=test_tenant.id,
            obj_id=created_tenant.id
        ))
        
        assert retrieved_tenant.id == created_tenant.id
        
        # Test update with tenant context
        update_data = {"name": "Updated Scoped Tenant"}
        updated_tenant = asyncio.run(tenant_scoped_service.update(
            db=db,
            tenant_id=test_tenant.id,
            obj_id=created_tenant.id,
            update_data=update_data,
            updated_by_id=test_user.id
        ))
        
        assert updated_tenant.name == update_data["name"]
        
        # Test delete with tenant context
        success = asyncio.run(tenant_scoped_service.delete(
            db=db,
            tenant_id=test_tenant.id,
            obj_id=created_tenant.id,
            deleted_by_id=test_user.id
        ))
        
        assert success is True
    
    def test_tenant_scoped_list_operations(self, db: Session, test_tenant: Tenant):
        """Test list operations with tenant scoping and filtering."""
        tenant_scoped_service = TenantScopedService(Tenant)
        
        # Test count
        count = asyncio.run(tenant_scoped_service.count(
            db=db,
            tenant_id=test_tenant.id
        ))
        
        assert isinstance(count, int)
        
        # Test list with filters
        tenants = asyncio.run(tenant_scoped_service.list_objects(
            db=db,
            tenant_id=test_tenant.id,
            skip=0,
            limit=10,
            filters={"status": TenantStatus.ACTIVE.value}
        ))
        
        assert isinstance(tenants, list)
    
    def test_tenant_access_validation(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test tenant access validation."""
        tenant_scoped_service = TenantScopedService(Tenant)
        
        # Test valid access (user is owner of test_tenant)
        access_valid = asyncio.run(tenant_scoped_service.validate_tenant_access(
            db=db,
            tenant_id=test_tenant.id,
            user_id=test_user.id
        ))
        
        assert access_valid is True
        
        # Test invalid access (user not in tenant)
        other_user = create_test_user(db, email="other@test.com")
        
        with pytest.raises(Exception):  # Should raise HTTPException
            asyncio.run(tenant_scoped_service.validate_tenant_access(
                db=db,
                tenant_id=test_tenant.id,
                user_id=other_user.id
            ))


class TestTenantAPIs:
    """Test suite for tenant management API endpoints."""
    
    def test_create_tenant_api(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test tenant creation API endpoint."""
        tenant_data = {
            "name": "API Test Tenant",
            "slug": "api-test-tenant",
            "contact_email": "api@test.com",
            "plan": "starter",
            "organization_type": "company"
        }
        
        response = client.post(
            "/api/v1/tenants/",
            json=tenant_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == tenant_data["name"]
        assert data["data"]["slug"] == tenant_data["slug"]
    
    def test_get_tenant_api(self, client: TestClient, auth_headers: Dict[str, str], test_tenant: Tenant):
        """Test get tenant API endpoint."""
        response = client.get(
            f"/api/v1/tenants/{test_tenant.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(test_tenant.id)
        assert data["data"]["name"] == test_tenant.name
    
    def test_list_tenants_api(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test list tenants API endpoint."""
        response = client.get(
            "/api/v1/tenants/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
    
    def test_update_tenant_api(self, client: TestClient, auth_headers: Dict[str, str], test_tenant: Tenant):
        """Test update tenant API endpoint."""
        update_data = {
            "name": "Updated API Tenant",
            "plan": "professional"
        }
        
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == update_data["name"]
        assert data["data"]["plan"] == update_data["plan"]
    
    def test_delete_tenant_api(self, client: TestClient, auth_headers: Dict[str, str], test_tenant: Tenant):
        """Test delete tenant API endpoint."""
        response = client.delete(
            f"/api/v1/tenants/{test_tenant.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is True
    
    def test_add_tenant_user_api(self, client: TestClient, auth_headers: Dict[str, str], 
                                test_tenant: Tenant, db: Session):
        """Test add tenant user API endpoint."""
        # Create a user to add
        new_user = create_test_user(db, email="newapi@test.com")
        
        user_data = {
            "user_id": str(new_user.id),
            "role": "admin",
            "permissions": {"can_manage_events": True}
        }
        
        response = client.post(
            f"/api/v1/tenants/{test_tenant.id}/users",
            json=user_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == str(new_user.id)
        assert data["data"]["role"] == "admin"
    
    def test_track_usage_api(self, client: TestClient, auth_headers: Dict[str, str], test_tenant: Tenant):
        """Test track usage API endpoint."""
        usage_data = {
            "metric": "events",
            "amount": 1
        }
        
        response = client.post(
            f"/api/v1/tenants/{test_tenant.id}/usage",
            json=usage_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is True
    
    def test_get_usage_stats_api(self, client: TestClient, auth_headers: Dict[str, str], test_tenant: Tenant):
        """Test get usage statistics API endpoint."""
        response = client.get(
            f"/api/v1/tenants/{test_tenant.id}/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "usage" in data["data"]
        assert "plan" in data["data"]
        assert "features_enabled" in data["data"]


class TestTenantDataSecurity:
    """Test suite for tenant data security and isolation verification."""
    
    def test_tenant_data_isolation(self, db: Session):
        """Test that tenants cannot access each other's data."""
        # Create two tenants
        tenant1 = create_test_tenant(db, slug="tenant1")
        tenant2 = create_test_tenant(db, slug="tenant2")
        
        # Test isolation verification
        isolation_results1 = rls_manager.verify_tenant_isolation(db, tenant1.id)
        isolation_results2 = rls_manager.verify_tenant_isolation(db, tenant2.id)
        
        assert isolation_results1["isolation_enabled"] is True
        assert isolation_results2["isolation_enabled"] is True
        assert isolation_results1["tenant_id"] == str(tenant1.id)
        assert isolation_results2["tenant_id"] == str(tenant2.id)
    
    def test_cross_tenant_access_prevention(self, db: Session):
        """Test that cross-tenant access is prevented."""
        # This would test actual cross-tenant data access attempts
        # Implementation depends on having actual tenant-scoped tables
        pass
    
    def test_system_admin_bypass(self, db: Session, test_tenant: Tenant):
        """Test that system admin can bypass tenant isolation."""
        with db_tenant_manager.system_admin_session(db):
            # In system admin context, should be able to access all tenant data
            current_admin = db.execute(
                text("SELECT current_setting('app.is_system_admin', true)")
            ).scalar()
            assert current_admin == "true"


# Performance and stress tests

class TestTenantPerformance:
    """Test suite for tenant management performance."""
    
    def test_bulk_tenant_operations(self, db: Session):
        """Test performance of bulk tenant operations."""
        # Test creating multiple tenants
        start_time = datetime.utcnow()
        
        tenants = []
        for i in range(10):
            user = create_test_user(db, email=f"bulk{i}@test.com")
            tenant = asyncio.run(tenant_service.create_tenant(
                db=db,
                creator_user_id=user.id,
                name=f"Bulk Tenant {i}",
                slug=f"bulk-tenant-{i}",
                contact_email=f"bulk{i}@test.com"
            ))
            tenants.append(tenant)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should create 10 tenants in reasonable time
        assert len(tenants) == 10
        assert duration < 30  # Should complete in under 30 seconds
    
    def test_tenant_list_performance(self, db: Session):
        """Test performance of tenant listing with many tenants."""
        # This would test listing performance with many tenants
        tenants = asyncio.run(tenant_service.list_tenants(
            db=db, skip=0, limit=100
        ))
        
        assert isinstance(tenants, list)
        # Additional performance assertions would go here


# Integration tests

class TestTenantIntegration:
    """Integration tests for tenant management with other systems."""
    
    def test_tenant_with_events_integration(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test tenant integration with events system."""
        # This would test that events are properly scoped to tenants
        # Requires events model and service to be implemented
        pass
    
    def test_tenant_with_teams_integration(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test tenant integration with teams system."""
        # This would test that teams are properly scoped to tenants
        pass
    
    def test_tenant_with_submissions_integration(self, db: Session, test_tenant: Tenant, test_user: User):
        """Test tenant integration with submissions system."""
        # This would test that submissions are properly scoped to tenants
        pass


if __name__ == "__main__":
    # Run specific test groups
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "TestTenantService or TestTenantUserManagement"
    ])
