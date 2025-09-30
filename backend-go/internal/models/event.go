package models

import (
	"database/sql/driver"
	"fmt"
	"strings"
	"time"
)

// StringArray represents a PostgreSQL string array
type StringArray []string

// Value implements the driver.Valuer interface for StringArray
func (a StringArray) Value() (driver.Value, error) {
	if len(a) == 0 {
		return "{}", nil
	}
	return fmt.Sprintf("{%s}", strings.Join(a, ",")), nil
}

// Scan implements the sql.Scanner interface for StringArray
func (a *StringArray) Scan(value interface{}) error {
	if value == nil {
		*a = StringArray{}
		return nil
	}

	str, ok := value.(string)
	if !ok {
		return fmt.Errorf("cannot scan %T into StringArray", value)
	}

	// Remove braces and split
	str = strings.Trim(str, "{}")
	if str == "" {
		*a = StringArray{}
		return nil
	}

	*a = StringArray(strings.Split(str, ","))
	return nil
}

// EventType represents the type of event
type EventType string

const (
	EventTypeInPerson EventType = "in_person"
	EventTypeVirtual  EventType = "virtual"
	EventTypeHybrid   EventType = "hybrid"
)

// EventStatus represents the status of an event
type EventStatus string

const (
	EventStatusDraft              EventStatus = "draft"
	EventStatusPublished          EventStatus = "published"
	EventStatusRegistrationOpen   EventStatus = "registration_open"
	EventStatusRegistrationClosed EventStatus = "registration_closed"
	EventStatusInProgress         EventStatus = "in_progress"
	EventStatusCompleted          EventStatus = "completed"
	EventStatusCancelled          EventStatus = "cancelled"
)

// EventVisibility represents the visibility of an event
type EventVisibility string

const (
	EventVisibilityPublic     EventVisibility = "public"
	EventVisibilityPrivate    EventVisibility = "private"
	EventVisibilityInviteOnly EventVisibility = "invite_only"
)

// Event represents a hackathon event
type Event struct {
	Base
	SoftDeleteMixin
	TenantMixin

	// Basic information
	Name             string  `gorm:"not null;size:200" json:"name"`
	Slug             string  `gorm:"not null;size:100;index" json:"slug"`
	Description      *string `gorm:"type:text" json:"description,omitempty"`
	ShortDescription *string `gorm:"size:500" json:"short_description,omitempty"`

	// Event type and status
	EventType  EventType       `gorm:"not null;default:'in_person';size:20" json:"event_type"`
	Status     EventStatus     `gorm:"not null;default:'draft';size:30" json:"status"`
	Visibility EventVisibility `gorm:"not null;default:'public';size:20" json:"visibility"`

	// Dates and timing
	StartDate             *time.Time `json:"start_date,omitempty"`
	EndDate               *time.Time `json:"end_date,omitempty"`
	RegistrationStartDate *time.Time `json:"registration_start_date,omitempty"`
	RegistrationEndDate   *time.Time `json:"registration_end_date,omitempty"`
	Timezone              string     `gorm:"not null;default:'UTC';size:50" json:"timezone"`

	// Location information
	VenueName    *string `gorm:"size:200" json:"venue_name,omitempty"`
	VenueAddress *string `gorm:"type:text" json:"venue_address,omitempty"`
	City         *string `gorm:"size:100" json:"city,omitempty"`
	Country      *string `gorm:"size:100" json:"country,omitempty"`
	VirtualURL   *string `gorm:"size:500" json:"virtual_url,omitempty"`

	// Capacity and limits
	MaxParticipants       *int `json:"max_participants,omitempty"`
	MaxTeamSize           *int `json:"max_team_size,omitempty"`
	MinTeamSize           *int `json:"min_team_size,omitempty"`
	AllowSoloParticipants bool `gorm:"not null;default:true" json:"allow_solo_participants"`

	// Event configuration
	RequireApproval     bool `gorm:"not null;default:false" json:"require_approval"`
	AllowTeamFormation  bool `gorm:"not null;default:true" json:"allow_team_formation"`
	AllowLateSubmission bool `gorm:"not null;default:false" json:"allow_late_submission"`

	// Themes and categories
	Theme      *string     `gorm:"size:200" json:"theme,omitempty"`
	Categories StringArray `gorm:"type:text[]" json:"categories"`
	Tags       StringArray `gorm:"type:text[]" json:"tags"`

	// Prizes and rewards
	PrizePool     *float64 `gorm:"type:decimal(10,2)" json:"prize_pool,omitempty"`
	PrizeCurrency *string  `gorm:"size:3" json:"prize_currency,omitempty"`

	// Contact and support
	ContactEmail *string `gorm:"size:255" json:"contact_email,omitempty"`
	SupportURL   *string `gorm:"size:500" json:"support_url,omitempty"`
	DiscordURL   *string `gorm:"size:500" json:"discord_url,omitempty"`
	SlackURL     *string `gorm:"size:500" json:"slack_url,omitempty"`

	// Branding and media
	LogoURL    *string `gorm:"size:500" json:"logo_url,omitempty"`
	BannerURL  *string `gorm:"size:500" json:"banner_url,omitempty"`
	WebsiteURL *string `gorm:"size:500" json:"website_url,omitempty"`

	// Social media
	TwitterHandle *string `gorm:"size:100" json:"twitter_handle,omitempty"`
	LinkedInURL   *string `gorm:"size:500" json:"linkedin_url,omitempty"`
	FacebookURL   *string `gorm:"size:500" json:"facebook_url,omitempty"`

	// Rules and guidelines
	Rules           *string `gorm:"type:text" json:"rules,omitempty"`
	JudgingCriteria *string `gorm:"type:text" json:"judging_criteria,omitempty"`
	CodeOfConduct   *string `gorm:"type:text" json:"code_of_conduct,omitempty"`

	// Event data as JSONB for flexibility
	EventData JSONB `gorm:"type:jsonb;default:'{}'" json:"event_data"`

	// Metrics and analytics
	ViewCount         int `gorm:"not null;default:0" json:"view_count"`
	RegistrationCount int `gorm:"not null;default:0" json:"registration_count"`
	SubmissionCount   int `gorm:"not null;default:0" json:"submission_count"`

	// Note: Relationships will be added when Team and Submission models are created
}

// TableName returns the table name for the Event model
func (Event) TableName() string {
	return "events"
}

// IsActive checks if the event is currently active
func (e *Event) IsActive() bool {
	return e.Status == EventStatusInProgress
}

// IsRegistrationOpen checks if registration is currently open
func (e *Event) IsRegistrationOpen() bool {
	if e.Status != EventStatusRegistrationOpen {
		return false
	}

	now := time.Now()
	if e.RegistrationStartDate != nil && now.Before(*e.RegistrationStartDate) {
		return false
	}
	if e.RegistrationEndDate != nil && now.After(*e.RegistrationEndDate) {
		return false
	}

	return true
}

// CanTransitionTo checks if the event can transition to the given status
func (e *Event) CanTransitionTo(newStatus EventStatus) bool {
	switch e.Status {
	case EventStatusDraft:
		return newStatus == EventStatusPublished
	case EventStatusPublished:
		return newStatus == EventStatusRegistrationOpen || newStatus == EventStatusCancelled
	case EventStatusRegistrationOpen:
		return newStatus == EventStatusRegistrationClosed || newStatus == EventStatusCancelled
	case EventStatusRegistrationClosed:
		return newStatus == EventStatusInProgress || newStatus == EventStatusCancelled
	case EventStatusInProgress:
		return newStatus == EventStatusCompleted || newStatus == EventStatusCancelled
	case EventStatusCompleted, EventStatusCancelled:
		return false
	default:
		return false
	}
}

// GetEventData retrieves a value from the event data JSONB field
func (e *Event) GetEventData(key string) interface{} {
	if e.EventData == nil {
		return nil
	}
	return e.EventData[key]
}

// SetEventData sets a value in the event data JSONB field
func (e *Event) SetEventData(key string, value interface{}) {
	if e.EventData == nil {
		e.EventData = make(JSONB)
	}
	e.EventData[key] = value
}
