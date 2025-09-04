"""
Event schemas for request/response validation
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

from app.models.event import EventType, EventStatus, EventVisibility


# Base schemas
class EventBase(BaseModel):
    """Base event schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Event name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly event identifier")
    description: Optional[str] = Field(None, description="Full event description")
    short_description: Optional[str] = Field(None, max_length=500, description="Brief event summary")
    
    # Event type and status
    event_type: EventType = Field(EventType.IN_PERSON, description="Event format")
    status: EventStatus = Field(EventStatus.DRAFT, description="Event status")
    visibility: EventVisibility = Field(EventVisibility.PUBLIC, description="Event visibility")
    
    # Timing
    timezone: str = Field("UTC", description="Event timezone")
    start_at: datetime = Field(..., description="Event start date and time")
    end_at: datetime = Field(..., description="Event end date and time")
    
    # Registration timing
    registration_start_at: Optional[datetime] = Field(None, description="Registration opens")
    registration_end_at: Optional[datetime] = Field(None, description="Registration closes")
    
    # Team formation timing
    team_formation_start_at: Optional[datetime] = Field(None, description="Team formation opens")
    team_formation_end_at: Optional[datetime] = Field(None, description="Team formation closes")
    
    # Submission timing
    submission_start_at: Optional[datetime] = Field(None, description="Submission period opens")
    submission_end_at: Optional[datetime] = Field(None, description="Submission deadline")
    
    # Judging timing
    judging_start_at: Optional[datetime] = Field(None, description="Judging period starts")
    judging_end_at: Optional[datetime] = Field(None, description="Judging period ends")
    
    # Capacity and limits
    capacity: Optional[int] = Field(None, ge=1, description="Maximum participants")
    min_team_size: int = Field(1, ge=1, le=10, description="Minimum team size")
    max_team_size: int = Field(4, ge=1, le=10, description="Maximum team size")
    max_teams: Optional[int] = Field(None, ge=1, description="Maximum number of teams")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        if v.startswith('-') or v.endswith('-') or '--' in v:
            raise ValueError('Slug cannot start/end with hyphens or contain consecutive hyphens')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_timing(cls, values):
        """Validate event timing constraints"""
        start_at = values.get('start_at')
        end_at = values.get('end_at')
        
        if start_at and end_at and start_at >= end_at:
            raise ValueError('Event end time must be after start time')
        
        # Validate registration timing
        reg_start = values.get('registration_start_at')
        reg_end = values.get('registration_end_at')
        
        if reg_start and reg_end and reg_start >= reg_end:
            raise ValueError('Registration end time must be after start time')
        
        if reg_end and start_at and reg_end > start_at:
            raise ValueError('Registration must end before event starts')
        
        # Validate team formation timing
        team_start = values.get('team_formation_start_at')
        team_end = values.get('team_formation_end_at')
        
        if team_start and team_end and team_start >= team_end:
            raise ValueError('Team formation end time must be after start time')
        
        # Validate submission timing
        sub_start = values.get('submission_start_at')
        sub_end = values.get('submission_end_at')
        
        if sub_start and sub_end and sub_start >= sub_end:
            raise ValueError('Submission end time must be after start time')
        
        if sub_end and end_at and sub_end > end_at:
            raise ValueError('Submission deadline cannot be after event ends')
        
        # Validate judging timing
        judge_start = values.get('judging_start_at')
        judge_end = values.get('judging_end_at')
        
        if judge_start and judge_end and judge_start >= judge_end:
            raise ValueError('Judging end time must be after start time')
        
        if judge_start and sub_end and judge_start < sub_end:
            raise ValueError('Judging cannot start before submission deadline')
        
        return values
    
    @root_validator(skip_on_failure=True)
    def validate_team_settings(cls, values):
        """Validate team formation settings"""
        min_size = values.get('min_team_size', 1)
        max_size = values.get('max_team_size', 4)
        
        if min_size > max_size:
            raise ValueError('Minimum team size cannot be greater than maximum team size')
        
        return values


class VenueInfo(BaseModel):
    """Venue information for in-person events"""
    name: Optional[str] = Field(None, max_length=200, description="Venue name")
    address: Optional[str] = Field(None, description="Full venue address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional venue data")


class VirtualInfo(BaseModel):
    """Virtual event information"""
    platform: Optional[str] = Field(None, max_length=100, description="Virtual platform (Zoom, Discord, etc.)")
    link: Optional[str] = Field(None, max_length=500, description="Virtual event link")
    config: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific configuration")


class BrandingInfo(BaseModel):
    """Event branding information"""
    logo_url: Optional[str] = Field(None, max_length=500, description="Event logo URL")
    banner_url: Optional[str] = Field(None, max_length=500, description="Event banner URL")
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Primary brand color")
    secondary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Secondary brand color")


class ContactInfo(BaseModel):
    """Event contact information"""
    contact_email: Optional[str] = Field(None, max_length=255, description="General contact email")
    support_email: Optional[str] = Field(None, max_length=255, description="Support contact email")
    website_url: Optional[str] = Field(None, max_length=500, description="Event website URL")
    social_links: Dict[str, str] = Field(default_factory=dict, description="Social media links")
    hashtags: List[str] = Field(default_factory=list, description="Event hashtags")


class RegistrationConfig(BaseModel):
    """Registration configuration"""
    requires_approval: bool = Field(False, description="Require manual approval for registration")
    requires_payment: bool = Field(False, description="Registration requires payment")
    registration_fee: Optional[int] = Field(None, ge=0, description="Registration fee in cents")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional registration settings")


class TeamFormationConfig(BaseModel):
    """Team formation configuration"""
    enabled: bool = Field(True, description="Enable team formation")
    allow_team_creation: bool = Field(True, description="Allow participants to create teams")
    allow_solo_participation: bool = Field(False, description="Allow solo participation")
    skills_matching_enabled: bool = Field(True, description="Enable skills-based matching")


class SubmissionConfig(BaseModel):
    """Submission configuration"""
    required_fields: List[str] = Field(default_factory=list, description="Required submission fields")
    max_file_size_mb: int = Field(100, ge=1, le=1000, description="Maximum file size in MB")
    allowed_file_types: List[str] = Field(default_factory=list, description="Allowed file extensions")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional submission settings")


class JudgingConfig(BaseModel):
    """Judging configuration"""
    public_voting_enabled: bool = Field(False, description="Enable public voting")
    peer_voting_enabled: bool = Field(False, description="Enable peer voting")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional judging settings")


class HardwareConfig(BaseModel):
    """Hardware and resources configuration"""
    provides_hardware: bool = Field(False, description="Event provides hardware")
    hardware_list: Dict[str, Any] = Field(default_factory=dict, description="Available hardware and quantities")


class PrizesConfig(BaseModel):
    """Prizes configuration"""
    total_prize_pool: Optional[int] = Field(None, ge=0, description="Total prize pool in cents")
    prizes_config: Dict[str, Any] = Field(default_factory=dict, description="Prize structure and rules")


# Request schemas
class EventCreate(EventBase):
    """Schema for creating events"""
    venue: Optional[VenueInfo] = None
    virtual: Optional[VirtualInfo] = None
    branding: Optional[BrandingInfo] = None
    contact: Optional[ContactInfo] = None
    registration: Optional[RegistrationConfig] = None
    team_formation: Optional[TeamFormationConfig] = None
    submission: Optional[SubmissionConfig] = None
    judging: Optional[JudgingConfig] = None
    hardware: Optional[HardwareConfig] = None
    prizes: Optional[PrizesConfig] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration fields")
    organizer_notes: Optional[str] = Field(None, description="Internal organizer notes")


class EventUpdate(BaseModel):
    """Schema for updating events"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    
    # Timing updates
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    team_formation_start_at: Optional[datetime] = None
    team_formation_end_at: Optional[datetime] = None
    submission_start_at: Optional[datetime] = None
    submission_end_at: Optional[datetime] = None
    judging_start_at: Optional[datetime] = None
    judging_end_at: Optional[datetime] = None
    
    # Capacity updates
    capacity: Optional[int] = Field(None, ge=1)
    min_team_size: Optional[int] = Field(None, ge=1, le=10)
    max_team_size: Optional[int] = Field(None, ge=1, le=10)
    max_teams: Optional[int] = Field(None, ge=1)
    
    # Configuration updates
    venue: Optional[VenueInfo] = None
    virtual: Optional[VirtualInfo] = None
    branding: Optional[BrandingInfo] = None
    contact: Optional[ContactInfo] = None
    registration: Optional[RegistrationConfig] = None
    team_formation: Optional[TeamFormationConfig] = None
    submission: Optional[SubmissionConfig] = None
    judging: Optional[JudgingConfig] = None
    hardware: Optional[HardwareConfig] = None
    prizes: Optional[PrizesConfig] = None
    custom_fields: Optional[Dict[str, Any]] = None
    organizer_notes: Optional[str] = None


class EventStatusUpdate(BaseModel):
    """Schema for updating event status"""
    status: EventStatus = Field(..., description="New event status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")


class EventStats(BaseModel):
    """Event statistics"""
    registered: int = Field(..., description="Number of registered participants")
    checked_in: int = Field(..., description="Number of checked-in participants")
    teams: int = Field(..., description="Number of teams formed")
    submissions: int = Field(..., description="Number of submissions")
    capacity: Optional[int] = Field(None, description="Event capacity")
    remaining: Optional[int] = Field(None, description="Remaining capacity")
    is_full: bool = Field(..., description="Whether event is at capacity")


# Response schemas
class EventResponse(EventBase):
    """Schema for event responses"""
    id: str = Field(..., description="Event ID")
    tenant_id: str = Field(..., description="Tenant ID")
    
    # Venue information
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    venue_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Virtual information
    virtual_platform: Optional[str] = None
    virtual_link: Optional[str] = None
    virtual_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Branding
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    
    # Contact
    contact_email: Optional[str] = None
    support_email: Optional[str] = None
    website_url: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)
    hashtags: List[str] = Field(default_factory=list)
    
    # Registration
    requires_approval: bool = False
    requires_payment: bool = False
    registration_fee: Optional[int] = None
    registration_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Team formation
    team_formation_enabled: bool = True
    allow_team_creation: bool = True
    allow_solo_participation: bool = False
    skills_matching_enabled: bool = True
    
    # Submission
    required_submission_fields: List[str] = Field(default_factory=list)
    max_file_size_mb: int = 100
    allowed_file_types: List[str] = Field(default_factory=list)
    submission_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Judging
    public_voting_enabled: bool = False
    peer_voting_enabled: bool = False
    judging_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Hardware
    provides_hardware: bool = False
    hardware_list: Dict[str, Any] = Field(default_factory=dict)
    
    # Prizes
    total_prize_pool: Optional[int] = None
    prizes_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Statistics
    registered_count: int = 0
    checked_in_count: int = 0
    teams_count: int = 0
    submissions_count: int = 0
    
    # Metadata
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    organizer_notes: Optional[str] = None
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed properties
    is_published: bool = Field(..., description="Whether event is published")
    is_registration_open: bool = Field(..., description="Whether registration is open")
    is_team_formation_open: bool = Field(..., description="Whether team formation is open")
    is_submission_open: bool = Field(..., description="Whether submission is open")
    is_judging_period: bool = Field(..., description="Whether judging is active")
    capacity_remaining: Optional[int] = Field(None, description="Remaining capacity")
    is_at_capacity: bool = Field(..., description="Whether at capacity")
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Schema for paginated event list responses"""
    events: List[EventResponse] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Events per page")
    total_pages: int = Field(..., description="Total number of pages")


# Wizard schemas for step-by-step event creation
class EventWizardStep1(BaseModel):
    """Event wizard step 1: Basic information"""
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    event_type: EventType = EventType.IN_PERSON


class EventWizardStep2(BaseModel):
    """Event wizard step 2: Timing"""
    timezone: str = "UTC"
    start_at: datetime
    end_at: datetime
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None


class EventWizardStep3(BaseModel):
    """Event wizard step 3: Venue/Virtual setup"""
    venue: Optional[VenueInfo] = None
    virtual: Optional[VirtualInfo] = None


class EventWizardStep4(BaseModel):
    """Event wizard step 4: Capacity and teams"""
    capacity: Optional[int] = Field(None, ge=1)
    min_team_size: int = Field(1, ge=1, le=10)
    max_team_size: int = Field(4, ge=1, le=10)
    max_teams: Optional[int] = Field(None, ge=1)
    team_formation: Optional[TeamFormationConfig] = None


class EventWizardStep5(BaseModel):
    """Event wizard step 5: Registration and submission"""
    registration: Optional[RegistrationConfig] = None
    submission: Optional[SubmissionConfig] = None
    team_formation_start_at: Optional[datetime] = None
    team_formation_end_at: Optional[datetime] = None
    submission_start_at: Optional[datetime] = None
    submission_end_at: Optional[datetime] = None


class EventWizardStep6(BaseModel):
    """Event wizard step 6: Final settings"""
    judging_start_at: Optional[datetime] = None
    judging_end_at: Optional[datetime] = None
    judging: Optional[JudgingConfig] = None
    hardware: Optional[HardwareConfig] = None
    prizes: Optional[PrizesConfig] = None
    branding: Optional[BrandingInfo] = None
    contact: Optional[ContactInfo] = None


# Schedule and resource management schemas
class ScheduleItem(BaseModel):
    """Individual schedule item"""
    id: Optional[str] = None
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    location: Optional[str] = Field(None, max_length=200)
    room_id: Optional[str] = None
    organizer: Optional[str] = Field(None, max_length=100)
    capacity: Optional[int] = Field(None, ge=1)
    registration_required: bool = False
    tags: List[str] = Field(default_factory=list)
    
    @root_validator(skip_on_failure=True)
    def validate_timing(cls, values):
        """Validate schedule item timing"""
        start_at = values.get('start_at')
        end_at = values.get('end_at')
        
        if start_at and end_at and start_at >= end_at:
            raise ValueError('End time must be after start time')
        
        return values


class Room(BaseModel):
    """Room/space information"""
    id: Optional[str] = None
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    capacity: int = Field(..., ge=1)
    location: Optional[str] = Field(None, max_length=200)
    equipment: List[str] = Field(default_factory=list)
    availability: List[Dict[str, Any]] = Field(default_factory=list)
    booking_rules: Dict[str, Any] = Field(default_factory=dict)


class ConflictDetection(BaseModel):
    """Schedule conflict detection result"""
    has_conflicts: bool
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# Waitlist schemas
class WaitlistEntry(BaseModel):
    """Waitlist entry"""
    id: str
    user_id: str
    position: int
    registered_at: datetime
    notified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: str  # waiting, notified, converted, expired


class WaitlistStats(BaseModel):
    """Waitlist statistics"""
    total_waiting: int
    total_notified: int
    total_converted: int
    conversion_rate: float
    average_wait_time: Optional[float] = None  # in hours
