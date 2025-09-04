"""
Core dependencies for FastAPI dependency injection.

This module provides common dependencies used across API endpoints including:
- Database session management
- Authentication and user context
- Tenant context and isolation
- Permission checking
"""

from typing import Optional, Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.services.tenant_service import tenant_service


# Security scheme for JWT token authentication
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Creates a new database session for each request and ensures
    it's properly closed after the request completes.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        db: Database session
        credentials: JWT token credentials
    
    Returns:
        Current authenticated user
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Validate token type
        token_type: str = payload.get("type")
        if token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return user


async def get_optional_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    
    This is useful for endpoints that can work with or without authentication.
    
    Args:
        db: Database session
        credentials: Optional JWT token credentials
    
    Returns:
        Current authenticated user or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(db, credentials)
    except HTTPException:
        return None


async def get_tenant_from_path(
    tenant_id: UUID,
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Get tenant from path parameter.
    
    Args:
        tenant_id: Tenant ID from path parameter
        db: Database session
    
    Returns:
        Tenant instance
    
    Raises:
        HTTPException: If tenant not found
    """
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


async def get_tenant_from_header(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """
    Get tenant from X-Tenant-ID header.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        Tenant instance or None if header not present
    
    Raises:
        HTTPException: If tenant ID is invalid or tenant not found
    """
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if not tenant_id_header:
        return None
    
    try:
        tenant_id = UUID(tenant_id_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
        )
    
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


async def get_tenant_from_subdomain(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """
    Get tenant from subdomain.
    
    Extracts tenant slug from subdomain and looks up the tenant.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        Tenant instance or None if no subdomain or tenant not found
    """
    host = request.headers.get("host", "")
    
    # Extract subdomain (assuming format: tenant.domain.com)
    host_parts = host.split(".")
    if len(host_parts) < 3:
        return None
    
    tenant_slug = host_parts[0]
    
    # Skip common subdomains
    if tenant_slug in ["www", "api", "admin", "app"]:
        return None
    
    tenant = await tenant_service.get_tenant_by_slug(db, tenant_slug)
    return tenant


async def get_current_tenant(
    tenant_from_path: Optional[Tenant] = Depends(get_tenant_from_path),
    tenant_from_header: Optional[Tenant] = Depends(get_tenant_from_header),
    tenant_from_subdomain: Optional[Tenant] = Depends(get_tenant_from_subdomain)
) -> Tenant:
    """
    Get current tenant context.
    
    Determines the current tenant from various sources in order of priority:
    1. Path parameter (for admin/management endpoints)
    2. X-Tenant-ID header
    3. Subdomain
    
    Args:
        tenant_from_path: Tenant from path parameter
        tenant_from_header: Tenant from header
        tenant_from_subdomain: Tenant from subdomain
    
    Returns:
        Current tenant
    
    Raises:
        HTTPException: If no tenant context can be determined
    """
    tenant = tenant_from_path or tenant_from_header or tenant_from_subdomain
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not found. Provide tenant ID in path, header, or subdomain."
        )
    
    return tenant


async def get_optional_tenant(
    tenant_from_header: Optional[Tenant] = Depends(get_tenant_from_header),
    tenant_from_subdomain: Optional[Tenant] = Depends(get_tenant_from_subdomain)
) -> Optional[Tenant]:
    """
    Get optional tenant context.
    
    Similar to get_current_tenant but returns None if no tenant context
    is found instead of raising an exception.
    
    Args:
        tenant_from_header: Tenant from header
        tenant_from_subdomain: Tenant from subdomain
    
    Returns:
        Current tenant or None
    """
    return tenant_from_header or tenant_from_subdomain


async def verify_tenant_access(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Verify that current user has access to current tenant.
    
    Args:
        current_user: Current authenticated user
        current_tenant: Current tenant context
        db: Database session
    
    Returns:
        Current tenant if access is allowed
    
    Raises:
        HTTPException: If user doesn't have access to tenant
    """
    # Get user's tenant memberships
    tenant_users = await tenant_service.get_tenant_users(
        db=db,
        tenant_id=current_tenant.id,
        active_only=True
    )
    
    # Check if user is a member of the tenant
    user_tenant = next(
        (tu for tu in tenant_users if tu.user_id == current_user.id),
        None
    )
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User is not a member of this tenant"
        )
    
    return current_tenant


async def require_tenant_admin(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Require that current user has admin access to current tenant.
    
    Args:
        current_user: Current authenticated user
        current_tenant: Current tenant context
        db: Database session
    
    Returns:
        Current tenant if admin access is allowed
    
    Raises:
        HTTPException: If user doesn't have admin access to tenant
    """
    # First verify basic tenant access
    await verify_tenant_access(current_user, current_tenant, db)
    
    # Get user's tenant memberships
    tenant_users = await tenant_service.get_tenant_users(
        db=db,
        tenant_id=current_tenant.id,
        active_only=True
    )
    
    # Check if user has admin role
    user_tenant = next(
        (tu for tu in tenant_users if tu.user_id == current_user.id),
        None
    )
    
    from app.core.rbac import TenantRole
    admin_roles = [TenantRole.OWNER.value, TenantRole.ADMIN.value]
    
    if not user_tenant or user_tenant.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin access required"
        )
    
    return current_tenant


async def require_tenant_owner(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Require that current user is owner of current tenant.
    
    Args:
        current_user: Current authenticated user
        current_tenant: Current tenant context
        db: Database session
    
    Returns:
        Current tenant if owner access is allowed
    
    Raises:
        HTTPException: If user is not the tenant owner
    """
    # First verify basic tenant access
    await verify_tenant_access(current_user, current_tenant, db)
    
    # Get user's tenant memberships
    tenant_users = await tenant_service.get_tenant_users(
        db=db,
        tenant_id=current_tenant.id,
        active_only=True
    )
    
    # Check if user is the owner
    user_tenant = next(
        (tu for tu in tenant_users if tu.user_id == current_user.id),
        None
    )
    
    from app.core.rbac import TenantRole
    
    if not user_tenant or user_tenant.role != TenantRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Tenant owner access required"
        )
    
    return current_tenant


# Pagination dependencies

class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        max_limit: int = 1000
    ):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), max_limit)
        self.page = (skip // limit) + 1 if limit > 0 else 1


def get_pagination_params(
    skip: int = 0,
    limit: int = 100
) -> PaginationParams:
    """
    Get pagination parameters with validation.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        Validated pagination parameters
    """
    return PaginationParams(skip=skip, limit=limit)
