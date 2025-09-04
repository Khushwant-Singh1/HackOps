"""
Role-Based Access Control (RBAC) System

This module provides:
- Role and permission management
- Tenant-isolated RBAC
- Permission checking and enforcement
- Role hierarchy and inheritance
- Dynamic permission evaluation
"""

from enum import Enum
from typing import List, Set, Dict, Any, Optional, Union
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.tenant import Tenant, TenantUser

class SystemRole(str, Enum):
    """System-wide roles."""
    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"
    SUPPORT = "support"

class TenantRole(str, Enum):
    """Tenant-specific roles."""
    OWNER = "owner"
    ADMIN = "admin" 
    MANAGER = "manager"
    ORGANIZER = "organizer"
    JUDGE = "judge"
    MENTOR = "mentor"
    PARTICIPANT = "participant"
    VOLUNTEER = "volunteer"
    SPONSOR = "sponsor"
    VIEWER = "viewer"

class Permission(str, Enum):
    """Granular permissions."""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Tenant management
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_BILLING = "tenant:billing"
    TENANT_SETTINGS = "tenant:settings"
    
    # Event management
    EVENT_CREATE = "event:create"
    EVENT_READ = "event:read"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"
    EVENT_PUBLISH = "event:publish"
    EVENT_ANALYTICS = "event:analytics"
    EVENT_SETTINGS = "event:settings"
    
    # Team management
    TEAM_CREATE = "team:create"
    TEAM_READ = "team:read"
    TEAM_UPDATE = "team:update"
    TEAM_DELETE = "team:delete"
    TEAM_JOIN = "team:join"
    TEAM_INVITE = "team:invite"
    TEAM_MANAGE = "team:manage"
    
    # Submission management
    SUBMISSION_CREATE = "submission:create"
    SUBMISSION_READ = "submission:read"
    SUBMISSION_UPDATE = "submission:update"
    SUBMISSION_DELETE = "submission:delete"
    SUBMISSION_SUBMIT = "submission:submit"
    SUBMISSION_JUDGE = "submission:judge"
    
    # Judging
    JUDGE_ASSIGN = "judge:assign"
    JUDGE_SCORE = "judge:score"
    JUDGE_REVIEW = "judge:review"
    JUDGE_FINAL = "judge:final"
    
    # Mentoring
    MENTOR_PROFILE = "mentor:profile"
    MENTOR_AVAILABILITY = "mentor:availability"
    MENTOR_SESSIONS = "mentor:sessions"
    
    # Communication
    COMM_SEND_ALL = "communication:send_all"
    COMM_SEND_ROLE = "communication:send_role"
    COMM_SEND_TEAM = "communication:send_team"
    COMM_ANNOUNCEMENTS = "communication:announcements"
    
    # Analytics and reporting
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_ADMIN = "analytics:admin"

@dataclass
class RoleDefinition:
    """Role definition with permissions."""
    name: str
    permissions: Set[Permission]
    inherits_from: Optional[List[str]] = None
    description: str = ""

class RBACManager:
    """Role-Based Access Control manager."""
    
    def __init__(self):
        self.role_definitions = self._initialize_roles()
        self.permission_cache: Dict[str, Set[Permission]] = {}
    
    def _initialize_roles(self) -> Dict[str, RoleDefinition]:
        """Initialize role definitions with permissions."""
        roles = {}
        
        # System roles
        roles[SystemRole.SUPER_ADMIN] = RoleDefinition(
            name=SystemRole.SUPER_ADMIN,
            permissions=set(Permission),  # All permissions
            description="Full system access"
        )
        
        roles[SystemRole.PLATFORM_ADMIN] = RoleDefinition(
            name=SystemRole.PLATFORM_ADMIN,
            permissions={
                Permission.TENANT_CREATE, Permission.TENANT_READ, Permission.TENANT_UPDATE,
                Permission.USER_READ, Permission.USER_LIST, Permission.USER_UPDATE,
                Permission.ANALYTICS_ADMIN, Permission.ANALYTICS_EXPORT,
                Permission.COMM_SEND_ALL
            },
            description="Platform administration"
        )
        
        roles[SystemRole.SUPPORT] = RoleDefinition(
            name=SystemRole.SUPPORT,
            permissions={
                Permission.TENANT_READ, Permission.USER_READ, Permission.USER_LIST,
                Permission.EVENT_READ, Permission.ANALYTICS_VIEW
            },
            description="Support and troubleshooting"
        )
        
        # Tenant roles
        roles[TenantRole.OWNER] = RoleDefinition(
            name=TenantRole.OWNER,
            permissions={
                Permission.TENANT_READ, Permission.TENANT_UPDATE, Permission.TENANT_DELETE,
                Permission.TENANT_BILLING, Permission.TENANT_SETTINGS,
                Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, 
                Permission.USER_DELETE, Permission.USER_LIST,
                Permission.EVENT_CREATE, Permission.EVENT_READ, Permission.EVENT_UPDATE,
                Permission.EVENT_DELETE, Permission.EVENT_PUBLISH, Permission.EVENT_ANALYTICS,
                Permission.EVENT_SETTINGS,
                Permission.JUDGE_ASSIGN, Permission.JUDGE_FINAL,
                Permission.COMM_SEND_ALL, Permission.COMM_ANNOUNCEMENTS,
                Permission.ANALYTICS_ADMIN, Permission.ANALYTICS_EXPORT
            },
            description="Tenant owner with full access"
        )
        
        roles[TenantRole.ADMIN] = RoleDefinition(
            name=TenantRole.ADMIN,
            permissions={
                Permission.TENANT_READ, Permission.TENANT_SETTINGS,
                Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_LIST,
                Permission.EVENT_CREATE, Permission.EVENT_READ, Permission.EVENT_UPDATE,
                Permission.EVENT_PUBLISH, Permission.EVENT_ANALYTICS, Permission.EVENT_SETTINGS,
                Permission.JUDGE_ASSIGN, Permission.COMM_SEND_ALL, Permission.COMM_ANNOUNCEMENTS,
                Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT
            },
            description="Tenant administrator"
        )
        
        roles[TenantRole.MANAGER] = RoleDefinition(
            name=TenantRole.MANAGER,
            permissions={
                Permission.EVENT_READ, Permission.EVENT_UPDATE, Permission.EVENT_ANALYTICS,
                Permission.USER_READ, Permission.USER_LIST,
                Permission.TEAM_READ, Permission.TEAM_MANAGE,
                Permission.SUBMISSION_READ, Permission.JUDGE_ASSIGN,
                Permission.COMM_SEND_ROLE, Permission.ANALYTICS_VIEW
            },
            description="Event and team manager"
        )
        
        roles[TenantRole.ORGANIZER] = RoleDefinition(
            name=TenantRole.ORGANIZER,
            permissions={
                Permission.EVENT_READ, Permission.EVENT_UPDATE,
                Permission.TEAM_READ, Permission.SUBMISSION_READ,
                Permission.COMM_SEND_ROLE, Permission.ANALYTICS_VIEW
            },
            description="Event organizer"
        )
        
        roles[TenantRole.JUDGE] = RoleDefinition(
            name=TenantRole.JUDGE,
            permissions={
                Permission.SUBMISSION_READ, Permission.SUBMISSION_JUDGE,
                Permission.JUDGE_SCORE, Permission.JUDGE_REVIEW,
                Permission.TEAM_READ
            },
            description="Project judge"
        )
        
        roles[TenantRole.MENTOR] = RoleDefinition(
            name=TenantRole.MENTOR,
            permissions={
                Permission.MENTOR_PROFILE, Permission.MENTOR_AVAILABILITY, Permission.MENTOR_SESSIONS,
                Permission.TEAM_READ, Permission.SUBMISSION_READ,
                Permission.USER_READ
            },
            description="Participant mentor"
        )
        
        roles[TenantRole.PARTICIPANT] = RoleDefinition(
            name=TenantRole.PARTICIPANT,
            permissions={
                Permission.TEAM_CREATE, Permission.TEAM_READ, Permission.TEAM_UPDATE,
                Permission.TEAM_JOIN, Permission.TEAM_INVITE,
                Permission.SUBMISSION_CREATE, Permission.SUBMISSION_READ, 
                Permission.SUBMISSION_UPDATE, Permission.SUBMISSION_SUBMIT,
                Permission.USER_READ
            },
            description="Event participant"
        )
        
        roles[TenantRole.VOLUNTEER] = RoleDefinition(
            name=TenantRole.VOLUNTEER,
            permissions={
                Permission.EVENT_READ, Permission.TEAM_READ, Permission.USER_READ
            },
            description="Event volunteer"
        )
        
        roles[TenantRole.SPONSOR] = RoleDefinition(
            name=TenantRole.SPONSOR,
            permissions={
                Permission.EVENT_READ, Permission.TEAM_READ, Permission.SUBMISSION_READ,
                Permission.ANALYTICS_VIEW
            },
            description="Event sponsor"
        )
        
        roles[TenantRole.VIEWER] = RoleDefinition(
            name=TenantRole.VIEWER,
            permissions={
                Permission.EVENT_READ, Permission.TEAM_READ, Permission.SUBMISSION_READ
            },
            description="Read-only access"
        )
        
        return roles
    
    def get_role_permissions(self, role: str) -> Set[Permission]:
        """Get all permissions for a role including inherited permissions."""
        if role in self.permission_cache:
            return self.permission_cache[role]
        
        permissions = set()
        role_def = self.role_definitions.get(role)
        
        if role_def:
            permissions.update(role_def.permissions)
            
            # Add inherited permissions
            if role_def.inherits_from:
                for parent_role in role_def.inherits_from:
                    permissions.update(self.get_role_permissions(parent_role))
        
        self.permission_cache[role] = permissions
        return permissions
    
    def has_permission(self, user_roles: List[str], permission: Permission, 
                      tenant_id: Optional[UUID] = None) -> bool:
        """Check if user has a specific permission."""
        for role in user_roles:
            role_permissions = self.get_role_permissions(role)
            if permission in role_permissions:
                return True
        return False
    
    def has_any_permission(self, user_roles: List[str], permissions: List[Permission],
                          tenant_id: Optional[UUID] = None) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(user_roles, perm, tenant_id) for perm in permissions)
    
    def has_all_permissions(self, user_roles: List[str], permissions: List[Permission],
                           tenant_id: Optional[UUID] = None) -> bool:
        """Check if user has all of the specified permissions."""
        return all(self.has_permission(user_roles, perm, tenant_id) for perm in permissions)
    
    def get_user_permissions(self, user_roles: List[str]) -> Set[Permission]:
        """Get all permissions for a user based on their roles."""
        permissions = set()
        for role in user_roles:
            permissions.update(self.get_role_permissions(role))
        return permissions
    
    def is_system_admin(self, user_roles: List[str]) -> bool:
        """Check if user has system admin privileges."""
        return any(role in [SystemRole.SUPER_ADMIN, SystemRole.PLATFORM_ADMIN] 
                  for role in user_roles)
    
    def is_tenant_admin(self, user_roles: List[str]) -> bool:
        """Check if user has tenant admin privileges."""
        return any(role in [TenantRole.OWNER, TenantRole.ADMIN] 
                  for role in user_roles)

class PermissionChecker:
    """Helper class for permission checking in routes."""
    
    def __init__(self, rbac_manager: RBACManager):
        self.rbac = rbac_manager
    
    async def get_user_roles(self, db: AsyncSession, user: User, 
                           tenant_id: Optional[UUID] = None) -> List[str]:
        """Get user roles for a specific tenant or system-wide."""
        roles = []
        
        # Add system roles from user profile
        if user.system_roles:
            roles.extend(user.system_roles)
        
        # Add tenant-specific roles
        if tenant_id:
            result = await db.execute(
                select(TenantUser.role)
                .where(TenantUser.user_id == user.id)
                .where(TenantUser.tenant_id == tenant_id)
                .where(TenantUser.is_active == True)
            )
            tenant_roles = [row[0] for row in result.fetchall()]
            roles.extend(tenant_roles)
        
        return roles
    
    async def check_permission(self, db: AsyncSession, user: User, 
                             permission: Permission, tenant_id: Optional[UUID] = None,
                             raise_exception: bool = True) -> bool:
        """Check if user has permission and optionally raise exception."""
        user_roles = await self.get_user_roles(db, user, tenant_id)
        has_perm = self.rbac.has_permission(user_roles, permission, tenant_id)
        
        if not has_perm and raise_exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        
        return has_perm
    
    async def check_any_permission(self, db: AsyncSession, user: User,
                                 permissions: List[Permission], 
                                 tenant_id: Optional[UUID] = None,
                                 raise_exception: bool = True) -> bool:
        """Check if user has any of the permissions."""
        user_roles = await self.get_user_roles(db, user, tenant_id)
        has_perm = self.rbac.has_any_permission(user_roles, permissions, tenant_id)
        
        if not has_perm and raise_exception:
            perm_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required any of: {', '.join(perm_names)}"
            )
        
        return has_perm
    
    async def check_tenant_access(self, db: AsyncSession, user: User, 
                                tenant_id: UUID, raise_exception: bool = True) -> bool:
        """Check if user has access to a tenant."""
        # System admins have access to all tenants
        user_roles = await self.get_user_roles(db, user)
        if self.rbac.is_system_admin(user_roles):
            return True
        
        # Check tenant membership
        result = await db.execute(
            select(TenantUser)
            .where(TenantUser.user_id == user.id)
            .where(TenantUser.tenant_id == tenant_id)
            .where(TenantUser.is_active == True)
        )
        has_access = result.scalar_one_or_none() is not None
        
        if not has_access and raise_exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        return has_access

# Global instances
rbac_manager = RBACManager()
permission_checker = PermissionChecker(rbac_manager)
