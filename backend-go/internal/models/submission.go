package models

import (
	"time"

	"github.com/google/uuid"
)

// SubmissionStatus represents the status of a submission
type SubmissionStatus string

const (
	SubmissionStatusDraft       SubmissionStatus = "draft"
	SubmissionStatusSubmitted   SubmissionStatus = "submitted"
	SubmissionStatusUnderReview SubmissionStatus = "under_review"
	SubmissionStatusApproved    SubmissionStatus = "approved"
	SubmissionStatusRejected    SubmissionStatus = "rejected"
)

// Submission represents a project submission for an event
type Submission struct {
	Base
	SoftDeleteMixin
	TenantMixin

	// Basic information
	Title       string  `gorm:"not null;size:200" json:"title"`
	Description *string `gorm:"type:text" json:"description,omitempty"`
	Summary     *string `gorm:"size:1000" json:"summary,omitempty"`

	// Submission status
	Status SubmissionStatus `gorm:"not null;default:'draft';size:20" json:"status"`

	// Event and team association
	EventID uuid.UUID  `gorm:"type:uuid;not null;index" json:"event_id"`
	TeamID  *uuid.UUID `gorm:"type:uuid;index" json:"team_id,omitempty"`
	UserID  uuid.UUID  `gorm:"type:uuid;not null;index" json:"user_id"` // Primary submitter

	// Project details
	GitHubURL        *string `gorm:"size:500" json:"github_url,omitempty"`
	DemoURL          *string `gorm:"size:500" json:"demo_url,omitempty"`
	VideoURL         *string `gorm:"size:500" json:"video_url,omitempty"`
	PresentationURL  *string `gorm:"size:500" json:"presentation_url,omitempty"`
	DocumentationURL *string `gorm:"size:500" json:"documentation_url,omitempty"`

	// Technical details
	TechnologiesUsed StringArray `gorm:"type:text[]" json:"technologies_used"`
	Categories       StringArray `gorm:"type:text[]" json:"categories"`
	Tags             StringArray `gorm:"type:text[]" json:"tags"`

	// Submission metadata
	SubmittedAt    *time.Time `json:"submitted_at,omitempty"`
	LastModifiedAt time.Time  `gorm:"not null;default:CURRENT_TIMESTAMP" json:"last_modified_at"`

	// Judging and feedback
	JudgeNotes     *string  `gorm:"type:text" json:"judge_notes,omitempty"`
	PublicFeedback *string  `gorm:"type:text" json:"public_feedback,omitempty"`
	Score          *float64 `gorm:"type:decimal(5,2)" json:"score,omitempty"`
	Rank           *int     `json:"rank,omitempty"`

	// Awards and recognition
	Awards     StringArray `gorm:"type:text[]" json:"awards"`
	IsFeatured bool        `gorm:"not null;default:false" json:"is_featured"`

	// Submission data as JSONB for flexibility
	SubmissionData JSONB `gorm:"type:jsonb;default:'{}'" json:"submission_data"`

	// File attachments (stored as JSON array of file metadata)
	Attachments JSONB `gorm:"type:jsonb;default:'[]'" json:"attachments"`
}

// TableName returns the table name for the Submission model
func (Submission) TableName() string {
	return "submissions"
}

// IsSubmitted checks if the submission has been submitted
func (s *Submission) IsSubmitted() bool {
	return s.Status != SubmissionStatusDraft
}

// CanEdit checks if the submission can still be edited
func (s *Submission) CanEdit() bool {
	return s.Status == SubmissionStatusDraft || s.Status == SubmissionStatusUnderReview
}

// Submit marks the submission as submitted
func (s *Submission) Submit() {
	if s.Status == SubmissionStatusDraft {
		s.Status = SubmissionStatusSubmitted
		now := time.Now()
		s.SubmittedAt = &now
	}
}

// GetSubmissionData retrieves a value from the submission data JSONB field
func (s *Submission) GetSubmissionData(key string) interface{} {
	if s.SubmissionData == nil {
		return nil
	}
	return s.SubmissionData[key]
}

// SetSubmissionData sets a value in the submission data JSONB field
func (s *Submission) SetSubmissionData(key string, value interface{}) {
	if s.SubmissionData == nil {
		s.SubmissionData = make(JSONB)
	}
	s.SubmissionData[key] = value
}
