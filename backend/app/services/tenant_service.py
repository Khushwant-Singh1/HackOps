"""
Tenant Management Service

This service handles all tenant-related operations including:
- Tenant creation and configuration management
- Usage tracking and billing foundations
- Tenant isolation and data access patterns
- Branding and customization support
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.tenant import Tenant, TenantUser, TenantStatus, TenantPlan
from app.models.user import User
from app.core.rbac import RBACManager, SystemRole, TenantRole, Permission


class TenantService:
    """Comprehensive tenant management service."""
    
    def __init__(self):
        self.rbac_manager = RBACManager()
    
    async def create_tenant(
        self,
        db: Session,
        creator_user_id: UUID,
        name: str,
        slug: str,
        contact_email: str,
        plan: str = TenantPlan.FREE.value,
        organization_type: Optional[str] = None,
        website_url: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        Create a new tenant with initial configuration.
        
        Args:
            db: Database session
            creator_user_id: ID of user creating the tenant
            name: Display name for the tenant
            slug: Unique URL-safe identifier
            contact_email: Primary contact email
            plan: Subscription plan (free, starter, professional, enterprise)
            organization_type: Type of organization (university, company, nonprofit)
            website_url: Organization website
            custom_settings: Additional configuration settings
        
        Returns:
            Created Tenant instance
        
        Raises:
            HTTPException: If tenant creation fails or slug already exists
        """
        try:
            # Validate slug is unique
            existing_tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
            if existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tenant slug '{slug}' already exists"
                )
            
            # Create tenant with default configuration
            tenant = Tenant(
                name=name,
                slug=slug,
                contact_email=contact_email,
                contact_name=None,  # Will be set from creator user info
                organization_type=organization_type,
                website_url=website_url,
                plan=plan,
                status=TenantStatus.ACTIVE.value,
                
                # Set usage limits based on plan
                **self._get_plan_limits(plan),
                
                # Default settings
                settings=custom_settings or {},
                branding_config=self._get_default_branding(),
                notification_config=self._get_default_notifications(),
                features_enabled=self._get_plan_features(plan)
            )
            
            db.add(tenant)
            db.flush()  # Get tenant ID without committing
            
            # Add creator as tenant owner
            await self._add_tenant_user(
                db=db,
                tenant_id=tenant.id,
                user_id=creator_user_id,
                role=TenantRole.OWNER.value,
                is_active=True
            )
            
            # Set contact name from creator user
            creator_user = db.query(User).filter(User.id == creator_user_id).first()
            if creator_user:
                tenant.contact_name = f"{creator_user.first_name} {creator_user.last_name}"
            
            db.commit()
            db.refresh(tenant)
            
            # Initialize tenant-specific data
            await self._initialize_tenant_data(db, tenant)
            
            return tenant
            
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create tenant due to data conflict"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create tenant: {str(e)}"
            )
    
    async def get_tenant(self, db: Session, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        return db.query(Tenant).filter(
            and_(Tenant.id == tenant_id, Tenant.is_deleted == False)
        ).first()
    
    async def get_tenant_by_slug(self, db: Session, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        return db.query(Tenant).filter(
            and_(Tenant.slug == slug, Tenant.is_deleted == False)
        ).first()
    
    async def list_tenants(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
        plan_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Tenant]:
        """
        List tenants with filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filter: Filter by tenant status
            plan_filter: Filter by subscription plan
            search: Search in name, slug, or contact_email
        
        Returns:
            List of tenants matching criteria
        """
        query = db.query(Tenant).filter(Tenant.is_deleted == False)
        
        # Apply filters
        if status_filter:
            query = query.filter(Tenant.status == status_filter)
        
        if plan_filter:
            query = query.filter(Tenant.plan == plan_filter)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Tenant.name.ilike(search_term),
                    Tenant.slug.ilike(search_term),
                    Tenant.contact_email.ilike(search_term)
                )
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        return query.all()
    
    async def update_tenant(
        self,
        db: Session,
        tenant_id: UUID,
        update_data: Dict[str, Any]
    ) -> Tenant:
        """
        Update tenant configuration.
        
        Args:
            db: Database session
            tenant_id: ID of tenant to update
            update_data: Dictionary of fields to update
        
        Returns:
            Updated Tenant instance
        
        Raises:
            HTTPException: If tenant not found or update fails
        """
        tenant = await self.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        try:
            # Update basic fields
            for field, value in update_data.items():
                if hasattr(tenant, field) and field not in ['id', 'created_at', 'updated_at']:
                    setattr(tenant, field, value)
            
            # Handle special update cases
            if 'plan' in update_data:
                await self._handle_plan_change(db, tenant, update_data['plan'])
            
            if 'branding_config' in update_data:
                tenant.branding_config = {**(tenant.branding_config or {}), **update_data['branding_config']}
            
            if 'settings' in update_data:
                tenant.settings = {**(tenant.settings or {}), **update_data['settings']}
            
            tenant.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(tenant)
            
            return tenant
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update tenant: {str(e)}"
            )
    
    async def delete_tenant(self, db: Session, tenant_id: UUID) -> bool:
        """
        Soft delete a tenant and all associated data.
        
        Args:
            db: Database session
            tenant_id: ID of tenant to delete
        
        Returns:
            True if deletion successful
        
        Raises:
            HTTPException: If tenant not found or deletion fails
        """
        tenant = await self.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        try:
            # Soft delete tenant
            tenant.is_deleted = True
            tenant.deleted_at = datetime.utcnow()
            tenant.status = TenantStatus.SUSPENDED.value
            
            # TODO: Soft delete all associated data
            # - Events
            # - Teams
            # - Submissions
            # - Tenant users
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete tenant: {str(e)}"
            )
    
    # Tenant User Management
    
    async def add_tenant_user(
        self,
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        role: str,
        invited_by_user_id: Optional[UUID] = None,
        permissions: Optional[Dict[str, Any]] = None
    ) -> TenantUser:
        """
        Add a user to a tenant with specified role.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
            user_id: ID of user to add
            role: Role to assign (owner, admin, member, viewer)
            invited_by_user_id: ID of user who sent invitation
            permissions: Custom permissions for the user
        
        Returns:
            Created TenantUser instance
        
        Raises:
            HTTPException: If tenant/user not found or already exists
        """
        # Validate tenant exists
        tenant = await self.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user already exists in tenant
        existing_tenant_user = db.query(TenantUser).filter(
            and_(TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id)
        ).first()
        
        if existing_tenant_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists in tenant"
            )
        
        return await self._add_tenant_user(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            invited_by_user_id=invited_by_user_id,
            permissions=permissions,
            is_active=True
        )
    
    async def remove_tenant_user(
        self,
        db: Session,
        tenant_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Remove a user from a tenant.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
            user_id: ID of user to remove
        
        Returns:
            True if removal successful
        
        Raises:
            HTTPException: If tenant user not found
        """
        tenant_user = db.query(TenantUser).filter(
            and_(TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id)
        ).first()
        
        if not tenant_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant"
            )
        
        try:
            db.delete(tenant_user)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove user from tenant: {str(e)}"
            )
    
    async def update_tenant_user_role(
        self,
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        new_role: str,
        permissions: Optional[Dict[str, Any]] = None
    ) -> TenantUser:
        """
        Update a tenant user's role and permissions.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
            user_id: ID of user
            new_role: New role to assign
            permissions: Updated permissions
        
        Returns:
            Updated TenantUser instance
        
        Raises:
            HTTPException: If tenant user not found
        """
        tenant_user = db.query(TenantUser).filter(
            and_(TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id)
        ).first()
        
        if not tenant_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant"
            )
        
        try:
            tenant_user.role = new_role
            if permissions:
                tenant_user.permissions = permissions
            
            db.commit()
            db.refresh(tenant_user)
            
            return tenant_user
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update tenant user role: {str(e)}"
            )
    
    async def get_tenant_users(
        self,
        db: Session,
        tenant_id: UUID,
        role_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[TenantUser]:
        """
        Get all users for a tenant.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
            role_filter: Filter by specific role
            active_only: Only return active users
        
        Returns:
            List of TenantUser instances
        """
        query = db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id)
        
        if role_filter:
            query = query.filter(TenantUser.role == role_filter)
        
        if active_only:
            query = query.filter(TenantUser.is_active == True)
        
        return query.all()
    
    # Usage Tracking and Billing
    
    async def track_usage(
        self,
        db: Session,
        tenant_id: UUID,
        metric: str,
        amount: int = 1
    ) -> bool:
        """
        Track usage for a specific metric.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
            metric: Metric to track (events, participants, storage)
            amount: Amount to increment
        
        Returns:
            True if tracking successful
        
        Raises:
            HTTPException: If tenant not found or usage limit exceeded
        """
        tenant = await self.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check usage limits
        current_usage = getattr(tenant, f"current_{metric}", 0)
        max_usage = getattr(tenant, f"max_{metric}", 0)
        
        if current_usage + amount > max_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Usage limit exceeded for {metric}. Current: {current_usage}, Max: {max_usage}"
            )
        
        try:
            # Update usage counter
            setattr(tenant, f"current_{metric}", current_usage + amount)
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to track usage: {str(e)}"
            )
    
    async def get_usage_stats(self, db: Session, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get usage statistics for a tenant.
        
        Args:
            db: Database session
            tenant_id: ID of tenant
        
        Returns:
            Dictionary with usage statistics
        """
        tenant = await self.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return {
            "plan": tenant.plan,
            "status": tenant.status,
            "usage": {
                "events": {
                    "current": tenant.current_events,
                    "max": tenant.max_events,
                    "percentage": tenant.get_usage_percentage("events")
                },
                "participants": {
                    "current": tenant.current_participants,
                    "max": tenant.max_participants_per_event,
                    "percentage": tenant.get_usage_percentage("participants")
                },
                "storage": {
                    "current": tenant.current_storage_gb,
                    "max": tenant.max_storage_gb,
                    "percentage": tenant.get_usage_percentage("storage_gb")
                },
                "admins": {
                    "current": tenant.current_admins,
                    "max": tenant.max_admins,
                    "percentage": tenant.get_usage_percentage("admins")
                }
            },
            "features_enabled": tenant.features_enabled,
            "subscription_ends_at": tenant.subscription_ends_at.isoformat() if tenant.subscription_ends_at else None,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None
        }
    
    # Private helper methods
    
    async def _add_tenant_user(
        self,
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        role: str,
        invited_by_user_id: Optional[UUID] = None,
        permissions: Optional[Dict[str, Any]] = None,
        is_active: bool = True
    ) -> TenantUser:
        """Internal method to add tenant user."""
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            permissions=permissions or {},
            is_active=is_active,
            invited_by_id=invited_by_user_id,
            joined_at=datetime.utcnow() if is_active else None
        )
        
        db.add(tenant_user)
        db.commit()
        db.refresh(tenant_user)
        
        return tenant_user
    
    def _get_plan_limits(self, plan: str) -> Dict[str, int]:
        """Get usage limits for a subscription plan."""
        plan_limits = {
            TenantPlan.FREE.value: {
                "max_events": 1,
                "max_participants_per_event": 50,
                "max_storage_gb": 1,
                "max_admins": 1
            },
            TenantPlan.STARTER.value: {
                "max_events": 5,
                "max_participants_per_event": 200,
                "max_storage_gb": 5,
                "max_admins": 3
            },
            TenantPlan.PROFESSIONAL.value: {
                "max_events": 20,
                "max_participants_per_event": 1000,
                "max_storage_gb": 25,
                "max_admins": 10
            },
            TenantPlan.ENTERPRISE.value: {
                "max_events": 100,
                "max_participants_per_event": 5000,
                "max_storage_gb": 100,
                "max_admins": 50
            }
        }
        
        return plan_limits.get(plan, plan_limits[TenantPlan.FREE.value])
    
    def _get_plan_features(self, plan: str) -> List[str]:
        """Get enabled features for a subscription plan."""
        plan_features = {
            TenantPlan.FREE.value: [
                "basic_events",
                "team_formation",
                "basic_submissions"
            ],
            TenantPlan.STARTER.value: [
                "basic_events",
                "team_formation",
                "basic_submissions",
                "custom_branding",
                "basic_analytics"
            ],
            TenantPlan.PROFESSIONAL.value: [
                "basic_events",
                "team_formation",
                "basic_submissions",
                "custom_branding",
                "basic_analytics",
                "advanced_judging",
                "sponsor_integration",
                "custom_domains"
            ],
            TenantPlan.ENTERPRISE.value: [
                "basic_events",
                "team_formation",
                "basic_submissions",
                "custom_branding",
                "basic_analytics",
                "advanced_judging",
                "sponsor_integration",
                "custom_domains",
                "sso_integration",
                "api_access",
                "white_label",
                "advanced_analytics"
            ]
        }
        
        return plan_features.get(plan, plan_features[TenantPlan.FREE.value])
    
    def _get_default_branding(self) -> Dict[str, Any]:
        """Get default branding configuration."""
        return {
            "primary_color": "#3B82F6",
            "secondary_color": "#64748B",
            "logo_url": None,
            "favicon_url": None,
            "custom_css": "",
            "footer_text": "Powered by HackOps"
        }
    
    def _get_default_notifications(self) -> Dict[str, Any]:
        """Get default notification configuration."""
        return {
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True,
            "reminder_intervals": [24, 1],  # hours before event
            "notification_types": {
                "registration_confirmation": True,
                "event_reminders": True,
                "team_invitations": True,
                "submission_deadlines": True,
                "judging_updates": True
            }
        }
    
    async def _handle_plan_change(self, db: Session, tenant: Tenant, new_plan: str) -> None:
        """Handle plan upgrade/downgrade logic."""
        old_plan = tenant.plan
        
        # Update plan limits
        new_limits = self._get_plan_limits(new_plan)
        for limit_key, limit_value in new_limits.items():
            setattr(tenant, limit_key, limit_value)
        
        # Update enabled features
        tenant.features_enabled = self._get_plan_features(new_plan)
        
        # Handle plan-specific logic
        if new_plan == TenantPlan.FREE.value:
            # Downgrading to free - may need to disable features
            tenant.custom_domain = None
            tenant.sso_enabled = False
        
        # Update subscription timing
        if new_plan != TenantPlan.FREE.value:
            if not tenant.subscription_ends_at:
                # New paid subscription
                tenant.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
    
    async def _initialize_tenant_data(self, db: Session, tenant: Tenant) -> None:
        """Initialize default data for a new tenant."""
        # Create default categories, templates, etc.
        # This would be expanded with actual initialization logic
        pass


# Tenant isolation context manager for data access
class TenantContext:
    """Context manager for tenant-scoped database operations."""
    
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self._original_tenant_id = None
    
    async def __aenter__(self):
        # Set tenant context for the current request/session
        # This would integrate with request context or session variables
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clear tenant context
        pass


# Global tenant service instance
tenant_service = TenantService()
