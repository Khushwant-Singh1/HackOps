"""
Database models for HackOps
"""

# Import base classes
from app.models.base import Base, SoftDeleteMixin, TenantMixin

# Import all models
from app.models.user import User, UserSession
from app.models.tenant import Tenant, TenantUser
from app.models.event import Event
from app.models.team import Team, TeamMember, TeamInvitation
from app.models.submission import Submission, SubmissionFile

# Export all models
__all__ = [
    # Base classes
    "Base",
    "SoftDeleteMixin", 
    "TenantMixin",
    
    # User models
    "User",
    "UserSession",
    
    # Tenant models
    "Tenant",
    "TenantUser",
    
    # Event models
    "Event",
    
    # Team models
    "Team",
    "TeamMember", 
    "TeamInvitation",
    
    # Submission models
    "Submission",
    "SubmissionFile",
]