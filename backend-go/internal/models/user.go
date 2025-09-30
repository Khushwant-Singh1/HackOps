package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

// JSONB is a custom type for handling PostgreSQL JSONB columns
type JSONB map[string]interface{}

// Value implements the driver.Valuer interface for JSONB
func (j JSONB) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// Scan implements the sql.Scanner interface for JSONB
func (j *JSONB) Scan(value interface{}) error {
	if value == nil {
		*j = make(JSONB)
		return nil
	}

	bytes, ok := value.([]byte)
	if !ok {
		return errors.New("type assertion to []byte failed")
	}

	return json.Unmarshal(bytes, j)
}

// User represents a user in the system
type User struct {
	Base
	SoftDeleteMixin

	// Authentication fields
	Email        string  `gorm:"uniqueIndex;not null;size:255" json:"email"`
	PasswordHash *string `gorm:"size:255" json:"-"` // Nullable for OAuth users
	IsActive     bool    `gorm:"not null;default:true" json:"is_active"`
	IsVerified   bool    `gorm:"not null;default:false" json:"is_verified"`

	// OAuth provider information
	AuthProvider *string `gorm:"size:50" json:"auth_provider,omitempty"`
	OAuthID      *string `gorm:"size:255" json:"oauth_id,omitempty"`

	// System-level roles
	SystemRole *string `gorm:"size:50" json:"system_role,omitempty"`

	// Profile information
	FirstName   string  `gorm:"not null;size:100" json:"first_name"`
	LastName    string  `gorm:"not null;size:100" json:"last_name"`
	DisplayName *string `gorm:"size:200" json:"display_name,omitempty"`
	AvatarURL   *string `gorm:"size:500" json:"avatar_url,omitempty"`
	Bio         *string `gorm:"type:text" json:"bio,omitempty"`

	// Personal information
	PhoneNumber *string    `gorm:"size:20" json:"phone_number,omitempty"`
	DateOfBirth *time.Time `json:"date_of_birth,omitempty"`
	MinorFlag   bool       `gorm:"not null;default:false" json:"minor_flag"`

	// Location
	Country       *string `gorm:"size:100" json:"country,omitempty"`
	StateProvince *string `gorm:"size:100" json:"state_province,omitempty"`
	City          *string `gorm:"size:100" json:"city,omitempty"`
	Timezone      string  `gorm:"not null;default:'UTC';size:50" json:"timezone"`

	// Skills and interests (for team matching)
	Skills          StringArray `gorm:"type:text[]" json:"skills"`
	Interests       StringArray `gorm:"type:text[]" json:"interests"`
	ExperienceLevel *string     `gorm:"size:20" json:"experience_level,omitempty"`

	// Social links
	GitHubUsername *string `gorm:"size:100" json:"github_username,omitempty"`
	LinkedInURL    *string `gorm:"size:500" json:"linkedin_url,omitempty"`
	PortfolioURL   *string `gorm:"size:500" json:"portfolio_url,omitempty"`

	// GDPR and consent management
	GDPRConsentAt         *time.Time `json:"gdpr_consent_at,omitempty"`
	MarketingConsent      bool       `gorm:"not null;default:false" json:"marketing_consent"`
	DataProcessingConsent bool       `gorm:"not null;default:false" json:"data_processing_consent"`

	// Profile data as JSONB for flexibility
	ProfileData JSONB `gorm:"type:jsonb;default:'{}'" json:"profile_data"`

	// Preferences and settings
	Preferences JSONB `gorm:"type:jsonb;default:'{}'" json:"preferences"`

	// Activity tracking
	LastLoginAt *time.Time `json:"last_login_at,omitempty"`
	LoginCount  int        `gorm:"not null;default:0" json:"login_count"`

	// Email verification
	EmailVerificationToken *string    `gorm:"size:255" json:"-"`
	EmailVerifiedAt        *time.Time `json:"email_verified_at,omitempty"`

	// Password reset
	PasswordResetToken     *string    `gorm:"size:255" json:"-"`
	PasswordResetExpiresAt *time.Time `json:"-"`

	// Relationships
	Sessions []UserSession `gorm:"foreignKey:UserID" json:"-"`
}

// TableName returns the table name for the User model
func (User) TableName() string {
	return "users"
}

// SetPassword hashes and sets the user's password
func (u *User) SetPassword(password string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	hashStr := string(hash)
	u.PasswordHash = &hashStr
	return nil
}

// VerifyPassword checks if the provided password matches the user's password
func (u *User) VerifyPassword(password string) bool {
	if u.PasswordHash == nil {
		return false
	}
	err := bcrypt.CompareHashAndPassword([]byte(*u.PasswordHash), []byte(password))
	return err == nil
}

// UpdateLastLogin updates the last login timestamp and increments the login count
func (u *User) UpdateLastLogin() {
	now := time.Now()
	u.LastLoginAt = &now
	u.LoginCount++
}

// FullName returns the user's full name
func (u *User) FullName() string {
	return fmt.Sprintf("%s %s", u.FirstName, u.LastName)
}

// IsMinor checks if the user is a minor
func (u *User) IsMinor() bool {
	return u.MinorFlag
}

// GetProfileData retrieves a value from the profile data JSONB field
func (u *User) GetProfileData(key string) interface{} {
	if u.ProfileData == nil {
		return nil
	}
	return u.ProfileData[key]
}

// SetProfileData sets a value in the profile data JSONB field
func (u *User) SetProfileData(key string, value interface{}) {
	if u.ProfileData == nil {
		u.ProfileData = make(JSONB)
	}
	u.ProfileData[key] = value
}

// GetPreference retrieves a user preference
func (u *User) GetPreference(key string) interface{} {
	if u.Preferences == nil {
		return nil
	}
	return u.Preferences[key]
}

// SetPreference sets a user preference
func (u *User) SetPreference(key string, value interface{}) {
	if u.Preferences == nil {
		u.Preferences = make(JSONB)
	}
	u.Preferences[key] = value
}

// UserSession represents a user session
type UserSession struct {
	Base

	UserID       uuid.UUID `gorm:"type:uuid;not null;index" json:"user_id"`
	SessionToken string    `gorm:"uniqueIndex;not null;size:255" json:"session_token"`
	RefreshToken *string   `gorm:"uniqueIndex;size:255" json:"refresh_token,omitempty"`
	ExpiresAt    time.Time `gorm:"not null" json:"expires_at"`
	IsActive     bool      `gorm:"not null;default:true" json:"is_active"`

	// Session metadata
	IPAddress  *string `gorm:"size:45" json:"ip_address,omitempty"` // IPv6 compatible
	UserAgent  *string `gorm:"type:text" json:"user_agent,omitempty"`
	DeviceInfo JSONB   `gorm:"type:jsonb;default:'{}'" json:"device_info"`

	// Relationships
	User User `gorm:"foreignKey:UserID" json:"-"`
}

// TableName returns the table name for the UserSession model
func (UserSession) TableName() string {
	return "user_sessions"
}

// IsExpired checks if the session is expired
func (s *UserSession) IsExpired() bool {
	return time.Now().After(s.ExpiresAt)
}

// Revoke revokes the session
func (s *UserSession) Revoke() {
	s.IsActive = false
}
