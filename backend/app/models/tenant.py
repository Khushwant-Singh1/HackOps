"""
Tenant model for multi-tenancy support
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.base import Base, SoftDeleteMixin


class TenantStatus(PyEnum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class TenantPlan(PyEnum):
    """Tenant subscription plan"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Tenant(Base, SoftDeleteMixin):
    """Tenant model for multi-tenant architecture"""
    
    __tablename__ = "tenants"
    
    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Contact information
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    
    # Organization details
    organization_type = Column(String(50), nullable=True)  # university, company, nonprofit, etc.
    website_url = Column(String(500), nullable=True)
    
    # Subscription and billing
    plan = Column(String(20), default=TenantPlan.FREE.value, nullable=False)
    status = Column(String(20), default=TenantStatus.ACTIVE.value, nullable=False)
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)
    
    # Usage limits and quotas
    max_events = Column(Integer, default=5, nullable=False)
    max_participants_per_event = Column(Integer, default=100, nullable=False)
    max_storage_gb = Column(Integer, default=1, nullable=False)
    max_admins = Column(Integer, default=2, nullable=False)
    
    # Current usage tracking
    current_events = Column(Integer, default=0, nullable=False)
    current_participants = Column(Integer, default=0, nullable=False)
    current_storage_gb = Column(Integer, default=0, nullable=False)
    current_admins = Column(Integer, default=0, nullable=False)
    
    # Branding and customization
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color code
    secondary_color = Column(String(7), nullable=True)
    custom_domain = Column(String(100), nullable=True, unique=True)
    
    # Feature flags
    features_enabled = Column(ARRAY(String), default=[], nullable=False)
    
    # Configuration as JSONB for flexibility
    settings = Column(JSONB, default={}, nullable=False)
    branding_config = Column(JSONB, default={}, nullable=False)
    notification_config = Column(JSONB, default={}, nullable=False)
    
    # API and integration settings
    api_rate_limit = Column(Integer, default=1000, nullable=False)  # requests per hour
    webhook_urls = Column(ARRAY(String), default=[], nullable=False)
    
    # Compliance and security
    data_retention_days = Column(Integer, default=365, nullable=False)
    gdpr_enabled = Column(Boolean, default=True, nullable=False)
    sso_enabled = Column(Boolean, default=False, nullable=False)
    sso_config = Column(JSONB, default={}, nullable=False)
    
    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.status == TenantStatus.ACTIVE.value and not self.is_deleted
    
    def is_trial(self) -> bool:
        """Check if tenant is on trial"""
        return self.status == TenantStatus.TRIAL.value
    
    def is_subscription_active(self) -> bool:
        """Check if subscription is active"""
        if self.subscription_ends_at:
            from datetime import datetime
            return datetime.utcnow() < self.subscription_ends_at
        return True
    
    def can_create_event(self) -> bool:
        """Check if tenant can create new events"""
        return (
            self.is_active() and 
            self.current_events < self.max_events and
            self.is_subscription_active()
        )
    
    def can_add_participants(self, count: int = 1) -> bool:
        """Check if tenant can add more participants"""
        return (
            self.is_active() and 
            (self.current_participants + count) <= self.max_participants_per_event
        )
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has specific feature enabled"""
        return feature in (self.features_enabled or [])
    
    def enable_feature(self, feature: str) -> None:
        """Enable a feature for tenant"""
        if not self.features_enabled:
            self.features_enabled = []
        if feature not in self.features_enabled:
            self.features_enabled.append(feature)
    
    def disable_feature(self, feature: str) -> None:
        """Disable a feature for tenant"""
        if self.features_enabled and feature in self.features_enabled:
            self.features_enabled.remove(feature)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get tenant setting"""
        return self.settings.get(key, default) if self.settings else default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set tenant setting"""
        if not self.settings:
            self.settings = {}
        self.settings[key] = value
    
    def increment_usage(self, metric: str, amount: int = 1) -> None:
        """Increment usage counter"""
        if hasattr(self, f"current_{metric}"):
            current_value = getattr(self, f"current_{metric}")
            setattr(self, f"current_{metric}", current_value + amount)
    
    def decrement_usage(self, metric: str, amount: int = 1) -> None:
        """Decrement usage counter"""
        if hasattr(self, f"current_{metric}"):
            current_value = getattr(self, f"current_{metric}")
            setattr(self, f"current_{metric}", max(0, current_value - amount))
    
    def get_usage_percentage(self, metric: str) -> float:
        """Get usage percentage for a metric"""
        current = getattr(self, f"current_{metric}", 0)
        maximum = getattr(self, f"max_{metric}", 1)
        return (current / maximum) * 100 if maximum > 0 else 0
    
    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"


class TenantUser(Base):
    """Many-to-many relationship between tenants and users with roles"""
    
    __tablename__ = "tenant_users"
    
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Role within the tenant
    role = Column(String(50), nullable=False)  # owner, admin, member, viewer
    
    # Permissions as JSONB for flexibility
    permissions = Column(JSONB, default={}, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    invited_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, nullable=True)
    
    # Invitation details
    invited_by_id = Column(UUID(as_uuid=True), nullable=True)
    invitation_token = Column(String(255), nullable=True, unique=True)
    invitation_expires_at = Column(DateTime, nullable=True)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission in tenant"""
        return self.permissions.get(permission, False) if self.permissions else False
    
    def grant_permission(self, permission: str) -> None:
        """Grant permission to user"""
        if not self.permissions:
            self.permissions = {}
        self.permissions[permission] = True
    
    def revoke_permission(self, permission: str) -> None:
        """Revoke permission from user"""
        if self.permissions and permission in self.permissions:
            self.permissions[permission] = False
    
    def is_admin(self) -> bool:
        """Check if user is admin or owner"""
        return self.role in ["owner", "admin"]
    
    def is_owner(self) -> bool:
        """Check if user is owner"""
        return self.role == "owner"
    
    def __repr__(self) -> str:
        return f"<TenantUser tenant_id={self.tenant_id} user_id={self.user_id} role={self.role}>"
