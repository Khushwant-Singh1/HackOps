"""
User model for authentication and profile management
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base, SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    """User model with authentication and profile data"""
    
    __tablename__ = "users"
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # OAuth provider information
    auth_provider = Column(String(50), nullable=True)  # google, github, microsoft, etc.
    oauth_id = Column(String(255), nullable=True)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Personal information
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    minor_flag = Column(Boolean, default=False, nullable=False)
    
    # Location
    country = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Skills and interests (for team matching)
    skills = Column(ARRAY(String), default=[], nullable=False)
    interests = Column(ARRAY(String), default=[], nullable=False)
    experience_level = Column(String(20), nullable=True)  # beginner, intermediate, advanced
    
    # Social links
    github_username = Column(String(100), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # GDPR and consent management
    gdpr_consent_at = Column(DateTime, nullable=True)
    marketing_consent = Column(Boolean, default=False, nullable=False)
    data_processing_consent = Column(Boolean, default=False, nullable=False)
    
    # Profile data as JSONB for flexibility
    profile_data = Column(JSONB, default={}, nullable=False)
    
    # Preferences and settings
    preferences = Column(JSONB, default={}, nullable=False)
    
    # Activity tracking
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    
    def set_password(self, password: str) -> None:
        """Set password hash"""
        from app.core.security import get_password_hash
        self.password_hash = get_password_hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password"""
        if not self.password_hash:
            return False
        from app.core.security import verify_password
        return verify_password(password, self.password_hash)
    
    def update_last_login(self) -> None:
        """Update last login timestamp and increment count"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_minor(self) -> bool:
        """Check if user is a minor"""
        return self.minor_flag
    
    def get_profile_data(self, key: str, default: Any = None) -> Any:
        """Get value from profile data JSONB"""
        return self.profile_data.get(key, default) if self.profile_data else default
    
    def set_profile_data(self, key: str, value: Any) -> None:
        """Set value in profile data JSONB"""
        if not self.profile_data:
            self.profile_data = {}
        self.profile_data[key] = value
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self.preferences.get(key, default) if self.preferences else default
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference"""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
    
    def add_skill(self, skill: str) -> None:
        """Add skill to user profile"""
        if not self.skills:
            self.skills = []
        if skill not in self.skills:
            self.skills.append(skill)
    
    def remove_skill(self, skill: str) -> None:
        """Remove skill from user profile"""
        if self.skills and skill in self.skills:
            self.skills.remove(skill)
    
    def add_interest(self, interest: str) -> None:
        """Add interest to user profile"""
        if not self.interests:
            self.interests = []
        if interest not in self.interests:
            self.interests.append(interest)
    
    def remove_interest(self, interest: str) -> None:
        """Remove interest from user profile"""
        if self.interests and interest in self.interests:
            self.interests.remove(interest)
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserSession(Base):
    """User session management"""
    
    __tablename__ = "user_sessions"
    
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSONB, default={}, nullable=False)
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def revoke(self) -> None:
        """Revoke session"""
        self.is_active = False
    
    def __repr__(self) -> str:
        return f"<UserSession {self.session_token[:8]}...>"
