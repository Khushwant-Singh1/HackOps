"""
Team model for team formation and collaboration
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.base import Base, SoftDeleteMixin, TenantMixin


class TeamStatus(PyEnum):
    """Team status enumeration"""
    FORMING = "forming"
    COMPLETE = "complete"
    LOCKED = "locked"
    DISBANDED = "disbanded"


class MemberStatus(PyEnum):
    """Team member status enumeration"""
    INVITED = "invited"
    ACTIVE = "active"
    LEFT = "left"
    REMOVED = "removed"


class TeamRole(PyEnum):
    """Team member role enumeration"""
    CAPTAIN = "captain"
    MEMBER = "member"


class Team(Base, SoftDeleteMixin, TenantMixin):
    """Team model for hackathon teams"""
    
    __tablename__ = "teams"
    
    # Event relationship
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tagline = Column(String(500), nullable=True)
    
    # Team captain
    captain_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Status and visibility
    status = Column(String(20), default=TeamStatus.FORMING.value, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    is_recruiting = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    # Size constraints
    min_size = Column(Integer, default=1, nullable=False)
    max_size = Column(Integer, default=4, nullable=False)
    current_size = Column(Integer, default=1, nullable=False)
    
    # Skills and requirements
    required_skills = Column(ARRAY(String), default=[], nullable=False)
    preferred_skills = Column(ARRAY(String), default=[], nullable=False)
    skill_requirements = Column(Text, nullable=True)
    
    # Team interests and focus
    interests = Column(ARRAY(String), default=[], nullable=False)
    focus_areas = Column(ARRAY(String), default=[], nullable=False)
    experience_level = Column(String(20), nullable=True)  # beginner, intermediate, advanced, mixed
    
    # Project information
    project_idea = Column(Text, nullable=True)
    project_tech_stack = Column(ARRAY(String), default=[], nullable=False)
    project_category = Column(String(100), nullable=True)
    
    # Track and challenge participation
    track_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    challenge_ids = Column(ARRAY(UUID), default=[], nullable=False)
    
    # Communication and collaboration
    discord_invite = Column(String(500), nullable=True)
    slack_channel = Column(String(500), nullable=True)
    github_repo = Column(String(500), nullable=True)
    communication_preferences = Column(JSONB, default={}, nullable=False)
    
    # Location preferences (for hybrid events)
    preferred_location = Column(String(200), nullable=True)
    timezone_preference = Column(String(50), nullable=True)
    
    # Team formation preferences
    looking_for_roles = Column(ARRAY(String), default=[], nullable=False)
    welcome_message = Column(Text, nullable=True)
    recruitment_status = Column(String(50), nullable=True)
    
    # Flexible team data
    team_data = Column(JSONB, default={}, nullable=False)
    
    # Statistics
    join_requests_count = Column(Integer, default=0, nullable=False)
    invitations_sent_count = Column(Integer, default=0, nullable=False)
    
    def is_full(self) -> bool:
        """Check if team is at maximum capacity"""
        return self.current_size >= self.max_size
    
    def can_accept_members(self) -> bool:
        """Check if team can accept new members"""
        return (
            not self.is_full() and
            self.is_recruiting and
            self.status == TeamStatus.FORMING.value and
            not self.is_locked
        )
    
    def has_skill_requirement(self, skill: str) -> bool:
        """Check if team requires a specific skill"""
        return skill in (self.required_skills or [])
    
    def prefers_skill(self, skill: str) -> bool:
        """Check if team prefers a specific skill"""
        return skill in (self.preferred_skills or [])
    
    def add_required_skill(self, skill: str) -> None:
        """Add required skill"""
        if not self.required_skills:
            self.required_skills = []
        if skill not in self.required_skills:
            self.required_skills.append(skill)
    
    def add_preferred_skill(self, skill: str) -> None:
        """Add preferred skill"""
        if not self.preferred_skills:
            self.preferred_skills = []
        if skill not in self.preferred_skills:
            self.preferred_skills.append(skill)
    
    def add_interest(self, interest: str) -> None:
        """Add team interest"""
        if not self.interests:
            self.interests = []
        if interest not in self.interests:
            self.interests.append(interest)
    
    def add_focus_area(self, area: str) -> None:
        """Add focus area"""
        if not self.focus_areas:
            self.focus_areas = []
        if area not in self.focus_areas:
            self.focus_areas.append(area)
    
    def add_tech_stack(self, tech: str) -> None:
        """Add technology to project tech stack"""
        if not self.project_tech_stack:
            self.project_tech_stack = []
        if tech not in self.project_tech_stack:
            self.project_tech_stack.append(tech)
    
    def add_challenge(self, challenge_id: str) -> None:
        """Add challenge participation"""
        if not self.challenge_ids:
            self.challenge_ids = []
        if challenge_id not in self.challenge_ids:
            self.challenge_ids.append(challenge_id)
    
    def remove_challenge(self, challenge_id: str) -> None:
        """Remove challenge participation"""
        if self.challenge_ids and challenge_id in self.challenge_ids:
            self.challenge_ids.remove(challenge_id)
    
    def lock_team(self) -> None:
        """Lock team (no more changes allowed)"""
        self.is_locked = True
        self.is_recruiting = False
        self.status = TeamStatus.LOCKED.value
    
    def unlock_team(self) -> None:
        """Unlock team"""
        self.is_locked = False
        if not self.is_full():
            self.is_recruiting = True
            self.status = TeamStatus.FORMING.value
    
    def set_complete(self) -> None:
        """Mark team as complete"""
        self.status = TeamStatus.COMPLETE.value
        self.is_recruiting = False
    
    def get_team_data(self, key: str, default: Any = None) -> Any:
        """Get value from team data JSONB"""
        return self.team_data.get(key, default) if self.team_data else default
    
    def set_team_data(self, key: str, value: Any) -> None:
        """Set value in team data JSONB"""
        if not self.team_data:
            self.team_data = {}
        self.team_data[key] = value
    
    def increment_stat(self, stat: str, amount: int = 1) -> None:
        """Increment team statistic"""
        if hasattr(self, f"{stat}_count"):
            current = getattr(self, f"{stat}_count")
            setattr(self, f"{stat}_count", current + amount)
    
    def __repr__(self) -> str:
        return f"<Team {self.slug}>"


class TeamMember(Base):
    """Team member model for managing team membership"""
    
    __tablename__ = "team_members"
    
    # Relationships
    team_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Role and status
    role = Column(String(20), default=TeamRole.MEMBER.value, nullable=False)
    status = Column(String(20), default=MemberStatus.ACTIVE.value, nullable=False)
    
    # Timestamps
    invited_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
    
    # Invitation details
    invited_by_id = Column(UUID(as_uuid=True), nullable=True)
    invitation_message = Column(Text, nullable=True)
    invitation_token = Column(String(255), nullable=True, unique=True)
    invitation_expires_at = Column(DateTime, nullable=True)
    
    # Member contributions and role
    skills_offered = Column(ARRAY(String), default=[], nullable=False)
    role_description = Column(String(200), nullable=True)
    contribution_notes = Column(Text, nullable=True)
    
    # Activity tracking
    last_active_at = Column(DateTime, nullable=True)
    contribution_score = Column(Integer, default=0, nullable=False)
    
    # Member preferences and availability
    availability = Column(JSONB, default={}, nullable=False)
    preferences = Column(JSONB, default={}, nullable=False)
    
    def is_captain(self) -> bool:
        """Check if member is team captain"""
        return self.role == TeamRole.CAPTAIN.value
    
    def is_active(self) -> bool:
        """Check if member is currently active"""
        return self.status == MemberStatus.ACTIVE.value
    
    def is_invited(self) -> bool:
        """Check if member is invited but not yet joined"""
        return self.status == MemberStatus.INVITED.value
    
    def accept_invitation(self) -> None:
        """Accept team invitation"""
        self.status = MemberStatus.ACTIVE.value
        self.joined_at = datetime.utcnow()
    
    def leave_team(self) -> None:
        """Leave team"""
        self.status = MemberStatus.LEFT.value
        self.left_at = datetime.utcnow()
    
    def remove_from_team(self) -> None:
        """Remove member from team"""
        self.status = MemberStatus.REMOVED.value
        self.left_at = datetime.utcnow()
    
    def promote_to_captain(self) -> None:
        """Promote member to captain"""
        self.role = TeamRole.CAPTAIN.value
    
    def demote_to_member(self) -> None:
        """Demote captain to member"""
        self.role = TeamRole.MEMBER.value
    
    def add_skill_offered(self, skill: str) -> None:
        """Add skill that member offers"""
        if not self.skills_offered:
            self.skills_offered = []
        if skill not in self.skills_offered:
            self.skills_offered.append(skill)
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_active_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<TeamMember team_id={self.team_id} user_id={self.user_id} role={self.role}>"


class TeamInvitation(Base):
    """Team invitation model for managing team join requests and invitations"""
    
    __tablename__ = "team_invitations"
    
    # Relationships
    team_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invited_by_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Invitation details
    invitation_type = Column(String(20), nullable=False)  # "invite" or "request"
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, declined, expired
    
    # Tokens and expiry
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Response
    responded_at = Column(DateTime, nullable=True)
    response_message = Column(Text, nullable=True)
    
    def is_expired(self) -> bool:
        """Check if invitation is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_pending(self) -> bool:
        """Check if invitation is still pending"""
        return self.status == "pending" and not self.is_expired()
    
    def accept(self, response_message: str = None) -> None:
        """Accept invitation"""
        self.status = "accepted"
        self.responded_at = datetime.utcnow()
        self.response_message = response_message
    
    def decline(self, response_message: str = None) -> None:
        """Decline invitation"""
        self.status = "declined"
        self.responded_at = datetime.utcnow()
        self.response_message = response_message
    
    def expire(self) -> None:
        """Mark invitation as expired"""
        self.status = "expired"
    
    def __repr__(self) -> str:
        return f"<TeamInvitation {self.invitation_type} team_id={self.team_id} user_id={self.user_id}>"
