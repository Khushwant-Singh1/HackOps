"""
Submission model for project submissions
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.base import Base, SoftDeleteMixin, TenantMixin


class SubmissionStatus(PyEnum):
    """Submission status enumeration"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    JUDGING = "judging"
    JUDGED = "judged"
    DISQUALIFIED = "disqualified"
    WITHDRAWN = "withdrawn"


class FileType(PyEnum):
    """File type enumeration"""
    PRESENTATION = "presentation"
    DEMO_VIDEO = "demo_video"
    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    IMAGE = "image"
    OTHER = "other"


class Submission(Base, SoftDeleteMixin, TenantMixin):
    """Submission model for hackathon project submissions"""
    
    __tablename__ = "submissions"
    
    # Relationships
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    submitted_by_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Basic information
    title = Column(String(200), nullable=False)
    tagline = Column(String(500), nullable=True)
    description = Column(Text, nullable=False)
    
    # Project details
    category = Column(String(100), nullable=True)
    tech_stack = Column(ARRAY(String), default=[], nullable=False)
    programming_languages = Column(ARRAY(String), default=[], nullable=False)
    frameworks = Column(ARRAY(String), default=[], nullable=False)
    
    # External links
    repository_url = Column(String(500), nullable=True)
    demo_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    presentation_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    
    # Track and challenge participation
    track_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    challenge_ids = Column(ARRAY(UUID), default=[], nullable=False)
    
    # Status and timing
    status = Column(String(20), default=SubmissionStatus.DRAFT.value, nullable=False)
    is_finalized = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    
    # Submission requirements compliance
    requirements_met = Column(JSONB, default={}, nullable=False)
    compliance_score = Column(Float, default=0.0, nullable=False)
    
    # Content and documentation
    problem_statement = Column(Text, nullable=True)
    solution_approach = Column(Text, nullable=True)
    technical_implementation = Column(Text, nullable=True)
    challenges_faced = Column(Text, nullable=True)
    future_improvements = Column(Text, nullable=True)
    
    # Team contribution details
    team_contributions = Column(JSONB, default={}, nullable=False)
    individual_contributions = Column(Text, nullable=True)
    
    # Innovation and impact
    innovation_description = Column(Text, nullable=True)
    market_potential = Column(Text, nullable=True)
    social_impact = Column(Text, nullable=True)
    
    # Technical details
    architecture_description = Column(Text, nullable=True)
    deployment_instructions = Column(Text, nullable=True)
    api_documentation = Column(Text, nullable=True)
    testing_approach = Column(Text, nullable=True)
    
    # Business aspects
    business_model = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    competitive_analysis = Column(Text, nullable=True)
    monetization_strategy = Column(Text, nullable=True)
    
    # Scoring and evaluation
    total_score = Column(Float, default=0.0, nullable=False)
    normalized_score = Column(Float, default=0.0, nullable=False)
    rank_position = Column(Integer, nullable=True)
    
    # Judge assignment and scoring
    assigned_judges_count = Column(Integer, default=0, nullable=False)
    completed_scores_count = Column(Integer, default=0, nullable=False)
    average_score = Column(Float, default=0.0, nullable=False)
    
    # Public engagement
    public_votes = Column(Integer, default=0, nullable=False)
    peer_votes = Column(Integer, default=0, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    
    # Plagiarism and validation
    plagiarism_checked = Column(Boolean, default=False, nullable=False)
    plagiarism_score = Column(Float, default=0.0, nullable=False)
    plagiarism_report = Column(JSONB, default={}, nullable=False)
    
    # Awards and recognition
    awards = Column(ARRAY(String), default=[], nullable=False)
    special_mentions = Column(ARRAY(String), default=[], nullable=False)
    prize_amount = Column(Integer, default=0, nullable=False)  # in cents
    
    # Submission metadata
    submission_data = Column(JSONB, default={}, nullable=False)
    revision_history = Column(JSONB, default=[], nullable=False)
    
    # Privacy and sharing
    is_public = Column(Boolean, default=True, nullable=False)
    allow_sharing = Column(Boolean, default=True, nullable=False)
    license_type = Column(String(100), nullable=True)
    
    def is_submitted(self) -> bool:
        """Check if submission is submitted (not draft)"""
        return self.status != SubmissionStatus.DRAFT.value
    
    def can_edit(self) -> bool:
        """Check if submission can still be edited"""
        return self.status in [SubmissionStatus.DRAFT.value] and not self.is_finalized
    
    def can_finalize(self) -> bool:
        """Check if submission can be finalized"""
        return self.status == SubmissionStatus.DRAFT.value and not self.is_finalized
    
    def finalize_submission(self) -> None:
        """Finalize the submission"""
        self.is_finalized = True
        self.finalized_at = datetime.utcnow()
        self.status = SubmissionStatus.SUBMITTED.value
        if not self.submitted_at:
            self.submitted_at = datetime.utcnow()
    
    def submit(self) -> None:
        """Submit the project"""
        if self.status == SubmissionStatus.DRAFT.value:
            self.status = SubmissionStatus.SUBMITTED.value
            self.submitted_at = datetime.utcnow()
    
    def start_review(self) -> None:
        """Start review process"""
        self.status = SubmissionStatus.UNDER_REVIEW.value
    
    def start_judging(self) -> None:
        """Start judging process"""
        self.status = SubmissionStatus.JUDGING.value
    
    def complete_judging(self) -> None:
        """Complete judging process"""
        self.status = SubmissionStatus.JUDGED.value
    
    def disqualify(self, reason: str = None) -> None:
        """Disqualify submission"""
        self.status = SubmissionStatus.DISQUALIFIED.value
        if reason:
            self.set_submission_data("disqualification_reason", reason)
    
    def withdraw(self) -> None:
        """Withdraw submission"""
        self.status = SubmissionStatus.WITHDRAWN.value
    
    def add_tech_stack(self, technology: str) -> None:
        """Add technology to tech stack"""
        if not self.tech_stack:
            self.tech_stack = []
        if technology not in self.tech_stack:
            self.tech_stack.append(technology)
    
    def add_programming_language(self, language: str) -> None:
        """Add programming language"""
        if not self.programming_languages:
            self.programming_languages = []
        if language not in self.programming_languages:
            self.programming_languages.append(language)
    
    def add_framework(self, framework: str) -> None:
        """Add framework"""
        if not self.frameworks:
            self.frameworks = []
        if framework not in self.frameworks:
            self.frameworks.append(framework)
    
    def add_challenge(self, challenge_id: str) -> None:
        """Add challenge participation"""
        if not self.challenge_ids:
            self.challenge_ids = []
        if challenge_id not in self.challenge_ids:
            self.challenge_ids.append(challenge_id)
    
    def add_award(self, award: str) -> None:
        """Add award to submission"""
        if not self.awards:
            self.awards = []
        if award not in self.awards:
            self.awards.append(award)
    
    def add_special_mention(self, mention: str) -> None:
        """Add special mention"""
        if not self.special_mentions:
            self.special_mentions = []
        if mention not in self.special_mentions:
            self.special_mentions.append(mention)
    
    def update_score(self, new_score: float) -> None:
        """Update submission score"""
        self.total_score = new_score
        self.add_revision("score_updated", {
            "previous_score": self.total_score,
            "new_score": new_score,
            "updated_at": datetime.utcnow().isoformat()
        })
    
    def increment_views(self) -> None:
        """Increment view count"""
        self.views_count += 1
    
    def add_public_vote(self) -> None:
        """Add public vote"""
        self.public_votes += 1
    
    def add_peer_vote(self) -> None:
        """Add peer vote"""
        self.peer_votes += 1
    
    def set_requirement_met(self, requirement: str, is_met: bool) -> None:
        """Set requirement compliance status"""
        if not self.requirements_met:
            self.requirements_met = {}
        self.requirements_met[requirement] = is_met
    
    def get_requirement_status(self, requirement: str) -> bool:
        """Get requirement compliance status"""
        return self.requirements_met.get(requirement, False) if self.requirements_met else False
    
    def calculate_compliance_score(self) -> float:
        """Calculate compliance score based on requirements"""
        if not self.requirements_met:
            return 0.0
        
        total_requirements = len(self.requirements_met)
        met_requirements = sum(1 for met in self.requirements_met.values() if met)
        
        return (met_requirements / total_requirements) * 100 if total_requirements > 0 else 0.0
    
    def get_submission_data(self, key: str, default: Any = None) -> Any:
        """Get value from submission data JSONB"""
        return self.submission_data.get(key, default) if self.submission_data else default
    
    def set_submission_data(self, key: str, value: Any) -> None:
        """Set value in submission data JSONB"""
        if not self.submission_data:
            self.submission_data = {}
        self.submission_data[key] = value
    
    def add_revision(self, action: str, data: Dict[str, Any]) -> None:
        """Add entry to revision history"""
        if not self.revision_history:
            self.revision_history = []
        
        revision = {
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        self.revision_history.append(revision)
    
    def get_completion_percentage(self) -> float:
        """Calculate submission completion percentage"""
        required_fields = [
            "title", "description", "repository_url"
        ]
        
        completed = 0
        for field in required_fields:
            if getattr(self, field):
                completed += 1
        
        return (completed / len(required_fields)) * 100
    
    def __repr__(self) -> str:
        return f"<Submission {self.title}>"


class SubmissionFile(Base):
    """File attachments for submissions"""
    
    __tablename__ = "submission_files"
    
    # Relationships
    submission_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_by_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    
    # Storage information
    storage_path = Column(String(500), nullable=False)
    storage_provider = Column(String(50), default="s3", nullable=False)
    public_url = Column(String(500), nullable=True)
    
    # File metadata
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    description = Column(Text, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    
    # Validation and security
    is_scanned = Column(Boolean, default=False, nullable=False)
    scan_result = Column(JSONB, default={}, nullable=False)
    is_safe = Column(Boolean, default=True, nullable=False)
    
    # Access control
    is_public = Column(Boolean, default=False, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    
    def increment_downloads(self) -> None:
        """Increment download count"""
        self.download_count += 1
    
    def mark_as_primary(self) -> None:
        """Mark file as primary"""
        self.is_primary = True
    
    def get_file_size_mb(self) -> float:
        """Get file size in MB"""
        return self.file_size / (1024 * 1024)
    
    def __repr__(self) -> str:
        return f"<SubmissionFile {self.filename}>"
