"""
Authentication and Authorization Middleware

This module provides FastAPI dependencies and middleware for:
- JWT token validation
- User authentication
- Permission checking
- Tenant context management
- Session management
"""

import secrets
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database_utils import get_db
from app.core.auth import token_manager, session_manager
from app.core.rbac import permission_checker, Permission, rbac_manager
from app.models.user import User, UserSession
from app.models.tenant import TenantUser

# Security scheme for token authentication
security = HTTPBearer(auto_error=False)

class AuthContext:
    """Authentication context for current request."""
    
    def __init__(self, user: User, session: Optional[UserSession] = None,
                 tenant_id: Optional[UUID] = None, roles: List[str] = None):
        self.user = user
        self.session = session
        self.tenant_id = tenant_id
        self.roles = roles or []
        self.permissions = rbac_manager.get_user_permissions(self.roles)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if current user has permission."""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if current user has any of the permissions."""
        return any(perm in self.permissions for perm in permissions)
    
    def is_system_admin(self) -> bool:
        """Check if current user is system admin."""
        return rbac_manager.is_system_admin(self.roles)
    
    def is_tenant_admin(self) -> bool:
        """Check if current user is tenant admin."""
        return rbac_manager.is_tenant_admin(self.roles)

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from JWT token."""
    if not credentials:
        return None
    
    try:
        # Verify and decode token
        user_data = token_manager.extract_user_data(credentials.credentials)
        user_id = user_data.get("user_id")
        
        if not user_id:
            return None
        
        # Get user from database
        result = await db.execute(
            select(User)
            .where(User.id == UUID(user_id))
            .where(User.is_active == True)
            .where(User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update last activity
            user.last_login_at = None  # Will be updated by session manager
        
        return user
        
    except (ValueError, HTTPException):
        return None

async def get_current_user_from_session(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from session token."""
    if not session_token:
        return None
    
    try:
        # Validate session
        session = await session_manager.validate_session(db, session_token)
        if not session:
            return None
        
        # Get user
        result = await db.execute(
            select(User)
            .where(User.id == session.user_id)
            .where(User.is_active == True)
            .where(User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        return user
        
    except Exception:
        return None

async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    session_user: Optional[User] = Depends(get_current_user_from_session)
) -> Optional[User]:
    """Get current user from token or session (token takes precedence)."""
    return token_user or session_user

async def require_authenticated_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require authenticated user, raise exception if not authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user

async def get_current_tenant_id(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[UUID]:
    """Extract tenant ID from request headers or path."""
    # Try to get tenant ID from header
    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        try:
            return UUID(tenant_header)
        except ValueError:
            pass
    
    # Try to get from path parameters
    path_params = request.path_params
    tenant_id = path_params.get("tenant_id")
    if tenant_id:
        try:
            return UUID(tenant_id)
        except ValueError:
            pass
    
    # If user is authenticated, try to get their default tenant
    if current_user and hasattr(current_user, 'default_tenant_id'):
        return current_user.default_tenant_id
    
    return None

async def get_auth_context(
    current_user: User = Depends(require_authenticated_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> AuthContext:
    """Get full authentication context with roles and permissions."""
    # Get user roles for the tenant
    roles = await permission_checker.get_user_roles(db, current_user, tenant_id)
    
    return AuthContext(
        user=current_user,
        tenant_id=tenant_id,
        roles=roles
    )

def require_permission(permission: Permission):
    """Dependency factory to require specific permission."""
    async def check_permission(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        if not auth_context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        return auth_context
    
    return check_permission

def require_any_permission(permissions: List[Permission]):
    """Dependency factory to require any of the specified permissions."""
    async def check_permissions(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        if not auth_context.has_any_permission(permissions):
            perm_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required any of: {', '.join(perm_names)}"
            )
        return auth_context
    
    return check_permissions

def require_tenant_access():
    """Dependency to require access to current tenant."""
    async def check_tenant_access(
        auth_context: AuthContext = Depends(get_auth_context),
        db: AsyncSession = Depends(get_db)
    ) -> AuthContext:
        if auth_context.tenant_id:
            await permission_checker.check_tenant_access(
                db, auth_context.user, auth_context.tenant_id
            )
        return auth_context
    
    return check_tenant_access

def require_system_admin():
    """Dependency to require system admin privileges."""
    async def check_system_admin(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        if not auth_context.is_system_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System administrator access required"
            )
        return auth_context
    
    return check_system_admin

def require_tenant_admin():
    """Dependency to require tenant admin privileges."""
    async def check_tenant_admin(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        if not auth_context.is_tenant_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant administrator access required"
            )
        return auth_context
    
    return check_tenant_admin

class StateManager:
    """Manages OAuth state tokens for CSRF protection."""
    
    def __init__(self):
        self.states: Dict[str, Dict[str, Any]] = {}
    
    def generate_state(self, redirect_url: Optional[str] = None) -> str:
        """Generate OAuth state token."""
        state = secrets.token_urlsafe(32)
        self.states[state] = {
            "redirect_url": redirect_url,
            "created_at": secrets.token_urlsafe(16)  # Simple timestamp placeholder
        }
        return state
    
    def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Validate and consume OAuth state token."""
        return self.states.pop(state, None)

# Global state manager
state_manager = StateManager()

# Optional dependencies (don't raise exceptions)
async def get_optional_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """Get current user without requiring authentication."""
    return current_user

async def get_optional_auth_context(
    current_user: Optional[User] = Depends(get_optional_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Optional[AuthContext]:
    """Get authentication context without requiring authentication."""
    if not current_user:
        return None
    
    roles = await permission_checker.get_user_roles(db, current_user, tenant_id)
    return AuthContext(
        user=current_user,
        tenant_id=tenant_id,
        roles=roles
    )


class AuthenticationMiddleware:
    """
    Simple authentication middleware placeholder.
    
    In a full implementation, this would handle:
    - Automatic token refresh
    - Session management
    - Request context setup
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # For now, just pass through to the app
        # In a full implementation, you would:
        # 1. Extract tokens from requests
        # 2. Validate and refresh tokens
        # 3. Set up request context
        # 4. Handle authentication errors
        
        await self.app(scope, receive, send)
