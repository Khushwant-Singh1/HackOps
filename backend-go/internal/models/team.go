package models

import (
	"github.com/google/uuid"
)

// TeamStatus represents the status of a team
type TeamStatus string

const (
	TeamStatusDraft    TeamStatus = "draft"
	TeamStatusActive   TeamStatus = "active"
	TeamStatusInactive TeamStatus = "inactive"
	TeamStatusArchived TeamStatus = "archived"
)

// Team represents a team in an event
type Team struct {
	Base
	SoftDeleteMixin
	TenantMixin

	// Basic information
	Name        string  `gorm:"not null;size:200" json:"name"`
	Slug        string  `gorm:"not null;size:100;index" json:"slug"`
	Description *string `gorm:"type:text" json:"description,omitempty"`

	// Team status
	Status TeamStatus `gorm:"not null;default:'draft';size:20" json:"status"`

	// Event association
	EventID uuid.UUID `gorm:"type:uuid;not null;index" json:"event_id"`

	// Team leader
	LeaderID uuid.UUID `gorm:"type:uuid;not null;index" json:"leader_id"`

	// Team settings
	IsLookingForMembers bool `gorm:"not null;default:true" json:"is_looking_for_members"`
	MaxMembers          int  `gorm:"not null;default:4" json:"max_members"`
	IsPublic            bool `gorm:"not null;default:true" json:"is_public"`

	// Skills and requirements
	RequiredSkills  StringArray `gorm:"type:text[]" json:"required_skills"`
	PreferredSkills StringArray `gorm:"type:text[]" json:"preferred_skills"`

	// Contact information
	ContactEmail *string `gorm:"size:255" json:"contact_email,omitempty"`
	DiscordURL   *string `gorm:"size:500" json:"discord_url,omitempty"`
	SlackURL     *string `gorm:"size:500" json:"slack_url,omitempty"`

	// Project information
	ProjectName        *string `gorm:"size:200" json:"project_name,omitempty"`
	ProjectDescription *string `gorm:"type:text" json:"project_description,omitempty"`
	GitHubURL          *string `gorm:"size:500" json:"github_url,omitempty"`

	// Team data as JSONB for flexibility
	TeamData JSONB `gorm:"type:jsonb;default:'{}'" json:"team_data"`

	// Relationships (will be added when TeamMember model is created)
	// Members []TeamMember `gorm:"foreignKey:TeamID" json:"-"`
}

// TableName returns the table name for the Team model
func (Team) TableName() string {
	return "teams"
}

// IsActive checks if the team is active
func (t *Team) IsActive() bool {
	return t.Status == TeamStatusActive
}

// GetTeamData retrieves a value from the team data JSONB field
func (t *Team) GetTeamData(key string) interface{} {
	if t.TeamData == nil {
		return nil
	}
	return t.TeamData[key]
}

// SetTeamData sets a value in the team data JSONB field
func (t *Team) SetTeamData(key string, value interface{}) {
	if t.TeamData == nil {
		t.TeamData = make(JSONB)
	}
	t.TeamData[key] = value
}
