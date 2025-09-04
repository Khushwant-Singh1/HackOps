"""
Tenant Management API Endpoints

This module provides REST API endpoints for tenant management including:
- Tenant CRUD operations
- Tenant user management
- Usage tracking and billing
- Tenant configuration and settings
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rbac import RBACManager, SystemRole, TenantRole, Permission
from app.models.user import User
from app.models.tenant import Tenant, TenantUser, TenantStatus, TenantPlan
from app.services.tenant_service import tenant_service
from app.schemas.base import BaseResponse, PaginatedResponse


router = APIRouter(prefix="/tenants", tags=["tenants"])


# Request/Response Schemas

class TenantCreateRequest(BaseModel):
    """Request schema for creating a new tenant."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the tenant")
    slug: str = Field(..., min_length=1, max_length=100, description="Unique URL-safe identifier")
    contact_email: str = Field(..., description="Primary contact email")
    plan: str = Field(default=TenantPlan.FREE.value, description="Subscription plan")
    organization_type: Optional[str] = Field(None, description="Type of organization")
    website_url: Optional[str] = Field(None, description="Organization website")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Additional configuration settings")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v
    
    @validator('plan')
    def validate_plan(cls, v):
        """Validate subscription plan."""
        if v not in [plan.value for plan in TenantPlan]:
            raise ValueError(f'Plan must be one of: {[plan.value for plan in TenantPlan]}')
        return v


class TenantUpdateRequest(BaseModel):
    """Request schema for updating a tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    organization_type: Optional[str] = None
    website_url: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    custom_domain: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    branding_config: Optional[Dict[str, Any]] = None
    notification_config: Optional[Dict[str, Any]] = None
    
    @validator('plan')
    def validate_plan(cls, v):
        """Validate subscription plan."""
        if v and v not in [plan.value for plan in TenantPlan]:
            raise ValueError(f'Plan must be one of: {[plan.value for plan in TenantPlan]}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        """Validate tenant status."""
        if v and v not in [status.value for status in TenantStatus]:
            raise ValueError(f'Status must be one of: {[status.value for status in TenantStatus]}')
        return v


class TenantResponse(BaseModel):
    """Response schema for tenant data."""
    id: UUID
    name: str
    slug: str
    contact_email: str
    contact_name: Optional[str]
    organization_type: Optional[str]
    website_url: Optional[str]
    plan: str
    status: str
    custom_domain: Optional[str]
    
    # Usage stats
    current_events: int
    max_events: int
    current_participants: int
    max_participants_per_event: int
    current_storage_gb: float
    max_storage_gb: float
    current_admins: int
    max_admins: int
    
    # Configuration
    settings: Dict[str, Any]
    branding_config: Dict[str, Any]
    notification_config: Dict[str, Any]
    features_enabled: List[str]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    trial_ends_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TenantSummaryResponse(BaseModel):
    """Summary response schema for tenant listing."""
    id: UUID
    name: str
    slug: str
    plan: str
    status: str
    current_events: int
    max_events: int
    usage_percentage: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantUserRequest(BaseModel):
    """Request schema for adding/updating tenant users."""
    user_id: UUID = Field(..., description="ID of user to add to tenant")
    role: str = Field(..., description="Role to assign to user")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Custom permissions for the user")
    
    @validator('role')
    def validate_role(cls, v):
        """Validate tenant role."""
        from app.core.rbac import TenantRole
        if v not in [role.value for role in TenantRole]:
            raise ValueError(f'Role must be one of: {[role.value for role in TenantRole]}')
        return v


class TenantUserResponse(BaseModel):
    """Response schema for tenant user data."""
    user_id: UUID
    tenant_id: UUID
    role: str
    permissions: Dict[str, Any]
    is_active: bool
    joined_at: Optional[datetime]
    invited_by_id: Optional[UUID]
    
    # User details (joined from User model)
    user_email: Optional[str]
    user_name: Optional[str]
    
    class Config:
        from_attributes = True


class UsageTrackingRequest(BaseModel):
    """Request schema for tracking usage metrics."""
    metric: str = Field(..., description="Metric to track")
    amount: int = Field(default=1, ge=1, description="Amount to increment")
    
    @validator('metric')
    def validate_metric(cls, v):
        """Validate metric type."""
        valid_metrics = ['events', 'participants', 'storage', 'admins']
        if v not in valid_metrics:
            raise ValueError(f'Metric must be one of: {valid_metrics}')
        return v


class UsageStatsResponse(BaseModel):
    """Response schema for usage statistics."""
    plan: str
    status: str
    usage: Dict[str, Dict[str, Any]]
    features_enabled: List[str]
    subscription_ends_at: Optional[str]
    trial_ends_at: Optional[str]


# API Endpoints

@router.post("/", response_model=BaseResponse[TenantResponse])
async def create_tenant(
    request: TenantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new tenant.
    
    Creates a new tenant with the specified configuration and adds the
    current user as the tenant owner.
    """
    try:
        tenant = await tenant_service.create_tenant(
            db=db,
            creator_user_id=current_user.id,
            name=request.name,
            slug=request.slug,
            contact_email=request.contact_email,
            plan=request.plan,
            organization_type=request.organization_type,
            website_url=request.website_url,
            custom_settings=request.custom_settings
        )
        
        return BaseResponse(
            success=True,
            message="Tenant created successfully",
            data=TenantResponse.from_orm(tenant)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/", response_model=PaginatedResponse[TenantSummaryResponse])
async def list_tenants(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status_filter: Optional[str] = Query(None, description="Filter by tenant status"),
    plan_filter: Optional[str] = Query(None, description="Filter by subscription plan"),
    search: Optional[str] = Query(None, description="Search in name, slug, or contact_email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List tenants with filtering and pagination.
    
    Returns a paginated list of tenants. System administrators can see all tenants,
    while regular users only see tenants they belong to.
    """
    try:
        # Check if user is system admin
        rbac_manager = RBACManager()
        is_system_admin = await rbac_manager.check_system_permission(
            current_user.id, Permission.MANAGE_TENANTS
        )
        
        if is_system_admin:
            # System admin can see all tenants
            tenants = await tenant_service.list_tenants(
                db=db,
                skip=skip,
                limit=limit,
                status_filter=status_filter,
                plan_filter=plan_filter,
                search=search
            )
        else:
            # Regular users only see their tenants
            # TODO: Implement user's tenant filtering
            tenants = []
        
        # Convert to summary responses with usage percentage
        tenant_summaries = []
        for tenant in tenants:
            usage_percentage = 0
            if tenant.max_events > 0:
                usage_percentage = (tenant.current_events / tenant.max_events) * 100
            
            summary = TenantSummaryResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                plan=tenant.plan,
                status=tenant.status,
                current_events=tenant.current_events,
                max_events=tenant.max_events,
                usage_percentage=round(usage_percentage, 2),
                created_at=tenant.created_at
            )
            tenant_summaries.append(summary)
        
        return PaginatedResponse(
            success=True,
            message="Tenants retrieved successfully",
            data=tenant_summaries,
            total=len(tenants),  # TODO: Get actual total count
            page=skip // limit + 1,
            page_size=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=BaseResponse[TenantResponse])
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tenant details by ID.
    
    Returns detailed information about a specific tenant.
    Users must have access to the tenant to view its details.
    """
    try:
        tenant = await tenant_service.get_tenant(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # TODO: Check user access to tenant
        
        return BaseResponse(
            success=True,
            message="Tenant retrieved successfully",
            data=TenantResponse.from_orm(tenant)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {str(e)}"
        )


@router.get("/slug/{slug}", response_model=BaseResponse[TenantResponse])
async def get_tenant_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tenant details by slug.
    
    Returns detailed information about a specific tenant identified by its slug.
    Users must have access to the tenant to view its details.
    """
    try:
        tenant = await tenant_service.get_tenant_by_slug(db, slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # TODO: Check user access to tenant
        
        return BaseResponse(
            success=True,
            message="Tenant retrieved successfully",
            data=TenantResponse.from_orm(tenant)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {str(e)}"
        )


@router.put("/{tenant_id}", response_model=BaseResponse[TenantResponse])
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update tenant configuration.
    
    Updates the specified tenant's configuration.
    Users must have admin access to the tenant to update it.
    """
    try:
        # TODO: Check user permissions for tenant admin
        
        # Convert request to dict, excluding None values
        update_data = request.dict(exclude_unset=True, exclude_none=True)
        
        tenant = await tenant_service.update_tenant(
            db=db,
            tenant_id=tenant_id,
            update_data=update_data
        )
        
        return BaseResponse(
            success=True,
            message="Tenant updated successfully",
            data=TenantResponse.from_orm(tenant)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.delete("/{tenant_id}", response_model=BaseResponse[bool])
async def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a tenant.
    
    Soft deletes the specified tenant and all associated data.
    Only tenant owners and system administrators can delete tenants.
    """
    try:
        # TODO: Check user permissions for tenant deletion
        
        success = await tenant_service.delete_tenant(db, tenant_id)
        
        return BaseResponse(
            success=success,
            message="Tenant deleted successfully" if success else "Failed to delete tenant",
            data=success
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}"
        )


# Tenant User Management Endpoints

@router.post("/{tenant_id}/users", response_model=BaseResponse[TenantUserResponse])
async def add_tenant_user(
    tenant_id: UUID,
    request: TenantUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a user to a tenant.
    
    Adds the specified user to the tenant with the given role.
    Users must have admin access to the tenant to add new users.
    """
    try:
        # TODO: Check user permissions for tenant admin
        
        tenant_user = await tenant_service.add_tenant_user(
            db=db,
            tenant_id=tenant_id,
            user_id=request.user_id,
            role=request.role,
            invited_by_user_id=current_user.id,
            permissions=request.permissions
        )
        
        return BaseResponse(
            success=True,
            message="User added to tenant successfully",
            data=TenantUserResponse.from_orm(tenant_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add user to tenant: {str(e)}"
        )


@router.get("/{tenant_id}/users", response_model=BaseResponse[List[TenantUserResponse]])
async def get_tenant_users(
    tenant_id: UUID,
    role_filter: Optional[str] = Query(None, description="Filter by user role"),
    active_only: bool = Query(True, description="Only return active users"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all users for a tenant.
    
    Returns a list of all users associated with the tenant.
    Users must have access to the tenant to view its user list.
    """
    try:
        # TODO: Check user access to tenant
        
        tenant_users = await tenant_service.get_tenant_users(
            db=db,
            tenant_id=tenant_id,
            role_filter=role_filter,
            active_only=active_only
        )
        
        return BaseResponse(
            success=True,
            message="Tenant users retrieved successfully",
            data=[TenantUserResponse.from_orm(tu) for tu in tenant_users]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant users: {str(e)}"
        )


@router.put("/{tenant_id}/users/{user_id}", response_model=BaseResponse[TenantUserResponse])
async def update_tenant_user_role(
    tenant_id: UUID,
    user_id: UUID,
    request: TenantUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a tenant user's role and permissions.
    
    Updates the role and permissions for the specified user in the tenant.
    Users must have admin access to the tenant to update user roles.
    """
    try:
        # TODO: Check user permissions for tenant admin
        
        tenant_user = await tenant_service.update_tenant_user_role(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            new_role=request.role,
            permissions=request.permissions
        )
        
        return BaseResponse(
            success=True,
            message="Tenant user role updated successfully",
            data=TenantUserResponse.from_orm(tenant_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant user role: {str(e)}"
        )


@router.delete("/{tenant_id}/users/{user_id}", response_model=BaseResponse[bool])
async def remove_tenant_user(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a user from a tenant.
    
    Removes the specified user from the tenant.
    Users must have admin access to the tenant to remove users.
    """
    try:
        # TODO: Check user permissions for tenant admin
        
        success = await tenant_service.remove_tenant_user(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        return BaseResponse(
            success=success,
            message="User removed from tenant successfully" if success else "Failed to remove user from tenant",
            data=success
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from tenant: {str(e)}"
        )


# Usage Tracking and Billing Endpoints

@router.post("/{tenant_id}/usage", response_model=BaseResponse[bool])
async def track_usage(
    tenant_id: UUID,
    request: UsageTrackingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Track usage for a specific metric.
    
    Records usage for the specified metric and checks against tenant limits.
    This endpoint is typically called by internal services.
    """
    try:
        # TODO: Check if this should be restricted to internal services
        
        success = await tenant_service.track_usage(
            db=db,
            tenant_id=tenant_id,
            metric=request.metric,
            amount=request.amount
        )
        
        return BaseResponse(
            success=success,
            message=f"Usage tracked successfully for {request.metric}",
            data=success
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track usage: {str(e)}"
        )


@router.get("/{tenant_id}/usage", response_model=BaseResponse[UsageStatsResponse])
async def get_usage_stats(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get usage statistics for a tenant.
    
    Returns detailed usage statistics including current usage,
    limits, and percentage utilization for all metrics.
    """
    try:
        # TODO: Check user access to tenant
        
        stats = await tenant_service.get_usage_stats(db, tenant_id)
        
        return BaseResponse(
            success=True,
            message="Usage statistics retrieved successfully",
            data=UsageStatsResponse(**stats)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage statistics: {str(e)}"
        )
