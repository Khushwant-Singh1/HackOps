"""
Event model for hackathon events
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.base import Base, SoftDeleteMixin, TenantMixin


class EventType(PyEnum):
    """Event type enumeration"""
    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class EventStatus(PyEnum):
    """Event status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventVisibility(PyEnum):
    """Event visibility enumeration"""
    PUBLIC = "public"
    PRIVATE = "private"
    INVITE_ONLY = "invite_only"


class Event(Base, SoftDeleteMixin, TenantMixin):
    """Event model for hackathon events"""
    
    __tablename__ = "events"
    
    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    
    # Event type and status
    event_type = Column(String(20), default=EventType.IN_PERSON.value, nullable=False)
    status = Column(String(30), default=EventStatus.DRAFT.value, nullable=False)
    visibility = Column(String(20), default=EventVisibility.PUBLIC.value, nullable=False)
    
    # Timing
    timezone = Column(String(50), default="UTC", nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    
    # Registration timing
    registration_start_at = Column(DateTime, nullable=True)
    registration_end_at = Column(DateTime, nullable=True)
    
    # Team formation timing
    team_formation_start_at = Column(DateTime, nullable=True)
    team_formation_end_at = Column(DateTime, nullable=True)
    
    # Submission timing
    submission_start_at = Column(DateTime, nullable=True)
    submission_end_at = Column(DateTime, nullable=True)
    
    # Judging timing
    judging_start_at = Column(DateTime, nullable=True)
    judging_end_at = Column(DateTime, nullable=True)
    
    # Capacity and limits
    capacity = Column(Integer, nullable=True)
    min_team_size = Column(Integer, default=1, nullable=False)
    max_team_size = Column(Integer, default=4, nullable=False)
    max_teams = Column(Integer, nullable=True)
    
    # Venue information (for in-person and hybrid events)
    venue_name = Column(String(200), nullable=True)
    venue_address = Column(Text, nullable=True)
    venue_city = Column(String(100), nullable=True)
    venue_country = Column(String(100), nullable=True)
    venue_data = Column(JSONB, default={}, nullable=False)
    
    # Virtual event information
    virtual_platform = Column(String(100), nullable=True)  # zoom, discord, teams, etc.
    virtual_link = Column(String(500), nullable=True)
    virtual_config = Column(JSONB, default={}, nullable=False)
    
    # Branding and media
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)
    secondary_color = Column(String(7), nullable=True)
    
    # Contact and support
    contact_email = Column(String(255), nullable=True)
    support_email = Column(String(255), nullable=True)
    website_url = Column(String(500), nullable=True)
    
    # Social media
    social_links = Column(JSONB, default={}, nullable=False)
    hashtags = Column(ARRAY(String), default=[], nullable=False)
    
    # Registration configuration
    registration_config = Column(JSONB, default={}, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    requires_payment = Column(Boolean, default=False, nullable=False)
    registration_fee = Column(Integer, nullable=True)  # in cents
    
    # Team formation settings
    team_formation_enabled = Column(Boolean, default=True, nullable=False)
    allow_team_creation = Column(Boolean, default=True, nullable=False)
    allow_solo_participation = Column(Boolean, default=False, nullable=False)
    skills_matching_enabled = Column(Boolean, default=True, nullable=False)
    
    # Submission settings
    submission_config = Column(JSONB, default={}, nullable=False)
    required_submission_fields = Column(ARRAY(String), default=[], nullable=False)
    max_file_size_mb = Column(Integer, default=100, nullable=False)
    allowed_file_types = Column(ARRAY(String), default=[], nullable=False)
    
    # Judging configuration
    judging_config = Column(JSONB, default={}, nullable=False)
    public_voting_enabled = Column(Boolean, default=False, nullable=False)
    peer_voting_enabled = Column(Boolean, default=False, nullable=False)
    
    # Rules and guidelines
    rules_url = Column(String(500), nullable=True)
    code_of_conduct_url = Column(String(500), nullable=True)
    terms_url = Column(String(500), nullable=True)
    privacy_policy_url = Column(String(500), nullable=True)
    
    # Hardware and resources
    provides_hardware = Column(Boolean, default=False, nullable=False)
    hardware_list = Column(JSONB, default={}, nullable=False)
    
    # Prizes and awards
    total_prize_pool = Column(Integer, nullable=True)  # in cents
    prizes_config = Column(JSONB, default={}, nullable=False)
    
    # Statistics (updated by triggers/jobs)
    registered_count = Column(Integer, default=0, nullable=False)
    checked_in_count = Column(Integer, default=0, nullable=False)
    teams_count = Column(Integer, default=0, nullable=False)
    submissions_count = Column(Integer, default=0, nullable=False)
    
    # Flexible configuration
    custom_fields = Column(JSONB, default={}, nullable=False)
    organizer_notes = Column(Text, nullable=True)
    
    def is_published(self) -> bool:
        """Check if event is published"""
        return self.status != EventStatus.DRAFT.value
    
    def is_registration_open(self) -> bool:
        """Check if registration is currently open"""
        now = datetime.utcnow()
        
        # Check status
        if self.status not in [EventStatus.REGISTRATION_OPEN.value, EventStatus.PUBLISHED.value]:
            return False
        
        # Check timing
        if self.registration_start_at and now < self.registration_start_at:
            return False
        
        if self.registration_end_at and now > self.registration_end_at:
            return False
        
        # Check capacity
        if self.capacity and self.registered_count >= self.capacity:
            return False
        
        return True
    
    def is_team_formation_open(self) -> bool:
        """Check if team formation is currently open"""
        if not self.team_formation_enabled:
            return False
        
        now = datetime.utcnow()
        
        if self.team_formation_start_at and now < self.team_formation_start_at:
            return False
        
        if self.team_formation_end_at and now > self.team_formation_end_at:
            return False
        
        return True
    
    def is_submission_open(self) -> bool:
        """Check if submission period is currently open"""
        now = datetime.utcnow()
        
        if self.submission_start_at and now < self.submission_start_at:
            return False
        
        if self.submission_end_at and now > self.submission_end_at:
            return False
        
        return self.status == EventStatus.IN_PROGRESS.value
    
    def is_judging_period(self) -> bool:
        """Check if judging period is active"""
        now = datetime.utcnow()
        
        if self.judging_start_at and now < self.judging_start_at:
            return False
        
        if self.judging_end_at and now > self.judging_end_at:
            return False
        
        return True
    
    def capacity_remaining(self) -> Optional[int]:
        """Get remaining capacity"""
        if self.capacity is None:
            return None
        return max(0, self.capacity - self.registered_count)
    
    def is_at_capacity(self) -> bool:
        """Check if event is at capacity"""
        if self.capacity is None:
            return False
        return self.registered_count >= self.capacity
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get value from any config JSONB field"""
        for config_field in ['registration_config', 'venue_data', 'virtual_config', 
                           'submission_config', 'judging_config', 'custom_fields']:
            config = getattr(self, config_field, {})
            if config and key in config:
                return config[key]
        return default
    
    def set_config(self, config_field: str, key: str, value: Any) -> None:
        """Set value in specific config JSONB field"""
        if hasattr(self, config_field):
            config = getattr(self, config_field) or {}
            config[key] = value
            setattr(self, config_field, config)
    
    def add_hashtag(self, hashtag: str) -> None:
        """Add hashtag to event"""
        if not self.hashtags:
            self.hashtags = []
        if hashtag not in self.hashtags:
            self.hashtags.append(hashtag)
    
    def remove_hashtag(self, hashtag: str) -> None:
        """Remove hashtag from event"""
        if self.hashtags and hashtag in self.hashtags:
            self.hashtags.remove(hashtag)
    
    def increment_stat(self, stat: str, amount: int = 1) -> None:
        """Increment event statistic"""
        if hasattr(self, f"{stat}_count"):
            current = getattr(self, f"{stat}_count")
            setattr(self, f"{stat}_count", current + amount)
    
    def decrement_stat(self, stat: str, amount: int = 1) -> None:
        """Decrement event statistic"""
        if hasattr(self, f"{stat}_count"):
            current = getattr(self, f"{stat}_count")
            setattr(self, f"{stat}_count", max(0, current - amount))
    
    def get_registration_stats(self) -> Dict[str, Any]:
        """Get registration statistics"""
        return {
            "registered": self.registered_count,
            "checked_in": self.checked_in_count,
            "capacity": self.capacity,
            "remaining": self.capacity_remaining() if self.capacity else None,
            "is_full": self.is_at_capacity()
        }
    
    def __repr__(self) -> str:
        return f"<Event {self.slug}>"
