package database

import (
	"time"

	"gorm.io/gorm"
)

// DB wraps gorm.DB with additional functionality
type DB struct {
	*gorm.DB
}

// NewDBWrapper wraps a gorm.DB instance with additional methods
func NewDBWrapper(db *gorm.DB) *DB {
	return &DB{DB: db}
}

// AutoMigrate runs auto migration for all models
func (db *DB) AutoMigrate() error {
	return db.DB.AutoMigrate(
		&User{},
		&Account{},
		&Session{},
		&VerificationToken{},
		&Tenant{},
		&Event{},
		&Team{},
		&Submission{},
	)
}

// HealthCheck checks database connectivity
func (db *DB) HealthCheck() error {
	sqlDB, err := db.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Ping()
}

// User represents a user in the database using GORM
type User struct {
	ID                     string                 `gorm:"type:varchar(255);primaryKey" json:"id"`
	Email                  string                 `gorm:"type:varchar(255);uniqueIndex;not null" json:"email"`
	PasswordHash           *string                `gorm:"type:varchar(255)" json:"-"`
	IsActive               bool                   `gorm:"default:true" json:"is_active"`
	IsVerified             bool                   `gorm:"default:false" json:"is_verified"`
	AuthProvider           *string                `gorm:"type:varchar(50)" json:"auth_provider"`
	OAuthID                *string                `gorm:"type:varchar(255)" json:"oauth_id"`
	SystemRole             *string                `gorm:"type:varchar(50)" json:"system_role"`
	FirstName              string                 `gorm:"type:varchar(100);not null" json:"first_name"`
	LastName               string                 `gorm:"type:varchar(100);not null" json:"last_name"`
	DisplayName            *string                `gorm:"type:varchar(200)" json:"display_name"`
	AvatarURL              *string                `gorm:"type:text" json:"avatar_url"`
	Bio                    *string                `gorm:"type:text" json:"bio"`
	PhoneNumber            *string                `gorm:"type:varchar(20)" json:"phone_number"`
	DateOfBirth            *time.Time             `json:"date_of_birth"`
	MinorFlag              bool                   `gorm:"default:false" json:"minor_flag"`
	Country                *string                `gorm:"type:varchar(100)" json:"country"`
	StateProvince          *string                `gorm:"type:varchar(100)" json:"state_province"`
	City                   *string                `gorm:"type:varchar(100)" json:"city"`
	Timezone               string                 `gorm:"type:varchar(50);default:'UTC'" json:"timezone"`
	Skills                 []string               `gorm:"type:text[]" json:"skills"`
	Interests              []string               `gorm:"type:text[]" json:"interests"`
	ExperienceLevel        *string                `gorm:"type:varchar(50)" json:"experience_level"`
	GitHubUsername         *string                `gorm:"type:varchar(100)" json:"github_username"`
	LinkedInURL            *string                `gorm:"type:text" json:"linkedin_url"`
	PortfolioURL           *string                `gorm:"type:text" json:"portfolio_url"`
	GDPRConsentAt          *time.Time             `json:"gdpr_consent_at"`
	MarketingConsent       bool                   `gorm:"default:false" json:"marketing_consent"`
	DataProcessingConsent  bool                   `gorm:"default:false" json:"data_processing_consent"`
	ProfileData            map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"profile_data"`
	Preferences            map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"preferences"`
	LastLoginAt            *time.Time             `json:"last_login_at"`
	LoginCount             int                    `gorm:"default:0" json:"login_count"`
	EmailVerificationToken *string                `gorm:"type:varchar(255)" json:"-"`
	EmailVerifiedAt        *time.Time             `json:"email_verified_at"`
	PasswordResetToken     *string                `gorm:"type:varchar(255)" json:"-"`
	PasswordResetExpiresAt *time.Time             `json:"-"`
	CreatedAt              time.Time              `json:"created_at"`
	UpdatedAt              time.Time              `json:"updated_at"`
	DeletedAt              gorm.DeletedAt         `gorm:"index" json:"deleted_at"`

	// Relations
	Sessions     []Session    `gorm:"foreignKey:UserID;constraint:OnDelete:CASCADE" json:"-"`
	Accounts     []Account    `gorm:"foreignKey:UserID;constraint:OnDelete:CASCADE" json:"-"`
	OwnedTenants []Tenant     `gorm:"foreignKey:OwnerID" json:"owned_tenants,omitempty"`
	Events       []Event      `gorm:"foreignKey:OrganizerID" json:"events,omitempty"`
	Teams        []Team       `gorm:"foreignKey:LeaderID" json:"teams,omitempty"`
	Submissions  []Submission `gorm:"foreignKey:UserID" json:"submissions,omitempty"`
}

// TableName specifies the table name for User
func (User) TableName() string {
	return "users"
}

// NextAuth.js Account model
type Account struct {
	ID                string  `gorm:"type:varchar(255);primaryKey" json:"id"`
	UserID            string  `gorm:"type:varchar(255);not null;index" json:"user_id"`
	Type              string  `gorm:"type:varchar(50);not null" json:"type"`
	Provider          string  `gorm:"type:varchar(50);not null" json:"provider"`
	ProviderAccountID string  `gorm:"type:varchar(255);not null" json:"provider_account_id"`
	RefreshToken      *string `gorm:"type:text" json:"refresh_token"`
	AccessToken       *string `gorm:"type:text" json:"access_token"`
	ExpiresAt         *int    `json:"expires_at"`
	TokenType         *string `gorm:"type:varchar(50)" json:"token_type"`
	Scope             *string `gorm:"type:text" json:"scope"`
	IDToken           *string `gorm:"type:text" json:"id_token"`
	SessionState      *string `gorm:"type:text" json:"session_state"`

	// Relations
	User User `gorm:"foreignKey:UserID;constraint:OnDelete:CASCADE" json:"-"`
}

// TableName specifies the table name for Account
func (Account) TableName() string {
	return "accounts"
}

// NextAuth.js Session model
type Session struct {
	ID           string    `gorm:"type:varchar(255);primaryKey" json:"id"`
	SessionToken string    `gorm:"type:varchar(255);uniqueIndex;not null" json:"session_token"`
	UserID       string    `gorm:"type:varchar(255);not null;index" json:"user_id"`
	Expires      time.Time `gorm:"not null" json:"expires"`

	// Relations
	User User `gorm:"foreignKey:UserID;constraint:OnDelete:CASCADE" json:"-"`
}

// TableName specifies the table name for Session
func (Session) TableName() string {
	return "sessions"
}

// NextAuth.js VerificationToken model
type VerificationToken struct {
	Identifier string    `gorm:"type:varchar(255);not null" json:"identifier"`
	Token      string    `gorm:"type:varchar(255);uniqueIndex;not null" json:"token"`
	Expires    time.Time `gorm:"not null" json:"expires"`
}

// TableName specifies the table name for VerificationToken
func (VerificationToken) TableName() string {
	return "verificationtokens"
}

// Tenant represents a tenant in the database
type Tenant struct {
	ID               string                 `gorm:"type:varchar(255);primaryKey" json:"id"`
	OwnerID          string                 `gorm:"type:varchar(255);not null;index" json:"owner_id"`
	Name             string                 `gorm:"type:varchar(200);not null" json:"name"`
	Slug             string                 `gorm:"type:varchar(100);uniqueIndex;not null" json:"slug"`
	Description      *string                `gorm:"type:text" json:"description"`
	Status           string                 `gorm:"type:varchar(50);default:'active'" json:"status"`
	Type             string                 `gorm:"type:varchar(50);default:'organization'" json:"type"`
	ContactEmail     *string                `gorm:"type:varchar(255)" json:"contact_email"`
	ContactPhone     *string                `gorm:"type:varchar(20)" json:"contact_phone"`
	ContactPerson    *string                `gorm:"type:varchar(200)" json:"contact_person"`
	Address          *string                `gorm:"type:text" json:"address"`
	City             *string                `gorm:"type:varchar(100)" json:"city"`
	StateProvince    *string                `gorm:"type:varchar(100)" json:"state_province"`
	Country          *string                `gorm:"type:varchar(100)" json:"country"`
	PostalCode       *string                `gorm:"type:varchar(20)" json:"postal_code"`
	LogoURL          *string                `gorm:"type:text" json:"logo_url"`
	WebsiteURL       *string                `gorm:"type:text" json:"website_url"`
	BrandColors      map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"brand_colors"`
	MaxEvents        *int                   `json:"max_events"`
	MaxUsers         *int                   `json:"max_users"`
	StorageLimit     *int64                 `json:"storage_limit"`
	IsCustomDomain   bool                   `gorm:"default:false" json:"is_custom_domain"`
	CustomDomain     *string                `gorm:"type:varchar(255)" json:"custom_domain"`
	Features         map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"features"`
	BillingEmail     *string                `gorm:"type:varchar(255)" json:"billing_email"`
	SubscriptionPlan *string                `gorm:"type:varchar(50)" json:"subscription_plan"`
	BillingData      map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"billing_data"`
	EventCount       int                    `gorm:"default:0" json:"event_count"`
	UserCount        int                    `gorm:"default:0" json:"user_count"`
	StorageUsed      int64                  `gorm:"default:0" json:"storage_used"`
	LastActiveAt     *time.Time             `json:"last_active_at"`
	TenantData       map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"tenant_data"`
	CreatedAt        time.Time              `json:"created_at"`
	UpdatedAt        time.Time              `json:"updated_at"`
	DeletedAt        gorm.DeletedAt         `gorm:"index" json:"deleted_at"`

	// Relations
	Owner  User    `gorm:"foreignKey:OwnerID" json:"owner,omitempty"`
	Events []Event `gorm:"foreignKey:TenantID" json:"events,omitempty"`
	Teams  []Team  `gorm:"foreignKey:TenantID" json:"teams,omitempty"`
}

// TableName specifies the table name for Tenant
func (Tenant) TableName() string {
	return "tenants"
}

// Event represents an event in the database
type Event struct {
	ID                    string                 `gorm:"type:varchar(255);primaryKey" json:"id"`
	TenantID              string                 `gorm:"type:varchar(255);not null;index" json:"tenant_id"`
	OrganizerID           string                 `gorm:"type:varchar(255);not null;index" json:"organizer_id"`
	Name                  string                 `gorm:"type:varchar(200);not null" json:"name"`
	Slug                  string                 `gorm:"type:varchar(100);not null" json:"slug"`
	Description           *string                `gorm:"type:text" json:"description"`
	ShortDescription      *string                `gorm:"type:varchar(500)" json:"short_description"`
	EventType             string                 `gorm:"type:varchar(50);default:'in_person'" json:"event_type"`
	Status                string                 `gorm:"type:varchar(50);default:'draft'" json:"status"`
	Visibility            string                 `gorm:"type:varchar(50);default:'public'" json:"visibility"`
	StartDate             *time.Time             `json:"start_date"`
	EndDate               *time.Time             `json:"end_date"`
	RegistrationStartDate *time.Time             `json:"registration_start_date"`
	RegistrationEndDate   *time.Time             `json:"registration_end_date"`
	Timezone              string                 `gorm:"type:varchar(50);default:'UTC'" json:"timezone"`
	VenueName             *string                `gorm:"type:varchar(200)" json:"venue_name"`
	VenueAddress          *string                `gorm:"type:text" json:"venue_address"`
	City                  *string                `gorm:"type:varchar(100)" json:"city"`
	Country               *string                `gorm:"type:varchar(100)" json:"country"`
	VirtualURL            *string                `gorm:"type:text" json:"virtual_url"`
	MaxParticipants       *int                   `json:"max_participants"`
	MaxTeamSize           *int                   `json:"max_team_size"`
	MinTeamSize           *int                   `json:"min_team_size"`
	AllowSoloParticipants bool                   `gorm:"default:true" json:"allow_solo_participants"`
	RequireApproval       bool                   `gorm:"default:false" json:"require_approval"`
	AllowTeamFormation    bool                   `gorm:"default:true" json:"allow_team_formation"`
	AllowLateSubmission   bool                   `gorm:"default:false" json:"allow_late_submission"`
	Theme                 *string                `gorm:"type:varchar(200)" json:"theme"`
	Categories            []string               `gorm:"type:text[]" json:"categories"`
	Tags                  []string               `gorm:"type:text[]" json:"tags"`
	PrizePool             *float64               `gorm:"type:decimal(10,2)" json:"prize_pool"`
	PrizeCurrency         *string                `gorm:"type:varchar(10)" json:"prize_currency"`
	ContactEmail          *string                `gorm:"type:varchar(255)" json:"contact_email"`
	SupportURL            *string                `gorm:"type:text" json:"support_url"`
	DiscordURL            *string                `gorm:"type:text" json:"discord_url"`
	SlackURL              *string                `gorm:"type:text" json:"slack_url"`
	LogoURL               *string                `gorm:"type:text" json:"logo_url"`
	BannerURL             *string                `gorm:"type:text" json:"banner_url"`
	WebsiteURL            *string                `gorm:"type:text" json:"website_url"`
	TwitterHandle         *string                `gorm:"type:varchar(100)" json:"twitter_handle"`
	LinkedInURL           *string                `gorm:"type:text" json:"linkedin_url"`
	FacebookURL           *string                `gorm:"type:text" json:"facebook_url"`
	Rules                 *string                `gorm:"type:text" json:"rules"`
	JudgingCriteria       *string                `gorm:"type:text" json:"judging_criteria"`
	CodeOfConduct         *string                `gorm:"type:text" json:"code_of_conduct"`
	EventData             map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"event_data"`
	ViewCount             int                    `gorm:"default:0" json:"view_count"`
	RegistrationCount     int                    `gorm:"default:0" json:"registration_count"`
	SubmissionCount       int                    `gorm:"default:0" json:"submission_count"`
	CreatedAt             time.Time              `json:"created_at"`
	UpdatedAt             time.Time              `json:"updated_at"`
	DeletedAt             gorm.DeletedAt         `gorm:"index" json:"deleted_at"`

	// Relations
	Tenant      Tenant       `gorm:"foreignKey:TenantID" json:"tenant,omitempty"`
	Organizer   User         `gorm:"foreignKey:OrganizerID" json:"organizer,omitempty"`
	Teams       []Team       `gorm:"foreignKey:EventID" json:"teams,omitempty"`
	Submissions []Submission `gorm:"foreignKey:EventID" json:"submissions,omitempty"`
}

// TableName specifies the table name for Event
func (Event) TableName() string {
	return "events"
}

// Team represents a team in the database
type Team struct {
	ID                  string                 `gorm:"type:varchar(255);primaryKey" json:"id"`
	TenantID            string                 `gorm:"type:varchar(255);not null;index" json:"tenant_id"`
	EventID             string                 `gorm:"type:varchar(255);not null;index" json:"event_id"`
	LeaderID            string                 `gorm:"type:varchar(255);not null;index" json:"leader_id"`
	Name                string                 `gorm:"type:varchar(200);not null" json:"name"`
	Slug                string                 `gorm:"type:varchar(100);not null" json:"slug"`
	Description         *string                `gorm:"type:text" json:"description"`
	Status              string                 `gorm:"type:varchar(50);default:'draft'" json:"status"`
	IsLookingForMembers bool                   `gorm:"default:true" json:"is_looking_for_members"`
	MaxMembers          int                    `gorm:"default:4" json:"max_members"`
	IsPublic            bool                   `gorm:"default:true" json:"is_public"`
	RequiredSkills      []string               `gorm:"type:text[]" json:"required_skills"`
	PreferredSkills     []string               `gorm:"type:text[]" json:"preferred_skills"`
	ContactEmail        *string                `gorm:"type:varchar(255)" json:"contact_email"`
	DiscordURL          *string                `gorm:"type:text" json:"discord_url"`
	SlackURL            *string                `gorm:"type:text" json:"slack_url"`
	ProjectName         *string                `gorm:"type:varchar(200)" json:"project_name"`
	ProjectDescription  *string                `gorm:"type:text" json:"project_description"`
	GitHubURL           *string                `gorm:"type:text" json:"github_url"`
	TeamData            map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"team_data"`
	CreatedAt           time.Time              `json:"created_at"`
	UpdatedAt           time.Time              `json:"updated_at"`
	DeletedAt           gorm.DeletedAt         `gorm:"index" json:"deleted_at"`

	// Relations
	Tenant      Tenant       `gorm:"foreignKey:TenantID" json:"tenant,omitempty"`
	Event       Event        `gorm:"foreignKey:EventID" json:"event,omitempty"`
	Leader      User         `gorm:"foreignKey:LeaderID" json:"leader,omitempty"`
	Submissions []Submission `gorm:"foreignKey:TeamID" json:"submissions,omitempty"`
}

// TableName specifies the table name for Team
func (Team) TableName() string {
	return "teams"
}

// Submission represents a submission in the database
type Submission struct {
	ID               string                 `gorm:"type:varchar(255);primaryKey" json:"id"`
	EventID          string                 `gorm:"type:varchar(255);not null;index" json:"event_id"`
	TeamID           *string                `gorm:"type:varchar(255);index" json:"team_id"`
	UserID           string                 `gorm:"type:varchar(255);not null;index" json:"user_id"`
	Title            string                 `gorm:"type:varchar(200);not null" json:"title"`
	Description      *string                `gorm:"type:text" json:"description"`
	Summary          *string                `gorm:"type:varchar(1000)" json:"summary"`
	Status           string                 `gorm:"type:varchar(50);default:'draft'" json:"status"`
	GitHubURL        *string                `gorm:"type:text" json:"github_url"`
	DemoURL          *string                `gorm:"type:text" json:"demo_url"`
	VideoURL         *string                `gorm:"type:text" json:"video_url"`
	PresentationURL  *string                `gorm:"type:text" json:"presentation_url"`
	DocumentationURL *string                `gorm:"type:text" json:"documentation_url"`
	TechnologiesUsed []string               `gorm:"type:text[]" json:"technologies_used"`
	Categories       []string               `gorm:"type:text[]" json:"categories"`
	Tags             []string               `gorm:"type:text[]" json:"tags"`
	SubmittedAt      *time.Time             `json:"submitted_at"`
	LastModifiedAt   time.Time              `gorm:"default:CURRENT_TIMESTAMP" json:"last_modified_at"`
	JudgeNotes       *string                `gorm:"type:text" json:"judge_notes"`
	PublicFeedback   *string                `gorm:"type:text" json:"public_feedback"`
	Score            *float64               `gorm:"type:decimal(5,2)" json:"score"`
	Rank             *int                   `json:"rank"`
	Awards           []string               `gorm:"type:text[]" json:"awards"`
	IsFeatured       bool                   `gorm:"default:false" json:"is_featured"`
	SubmissionData   map[string]interface{} `gorm:"type:jsonb;default:'{}'" json:"submission_data"`
	Attachments      []string               `gorm:"type:text[]" json:"attachments"`
	CreatedAt        time.Time              `json:"created_at"`
	UpdatedAt        time.Time              `json:"updated_at"`
	DeletedAt        gorm.DeletedAt         `gorm:"index" json:"deleted_at"`

	// Relations
	Event     Event `gorm:"foreignKey:EventID" json:"event,omitempty"`
	Team      *Team `gorm:"foreignKey:TeamID" json:"team,omitempty"`
	Submitter User  `gorm:"foreignKey:UserID" json:"submitter,omitempty"`
}

// TableName specifies the table name for Submission
func (Submission) TableName() string {
	return "submissions"
}
