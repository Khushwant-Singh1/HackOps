package models

import (
	"github.com/google/uuid"
)

// TenantStatus represents the status of a tenant
type TenantStatus string

const (
	TenantStatusActive    TenantStatus = "active"
	TenantStatusInactive  TenantStatus = "inactive"
	TenantStatusSuspended TenantStatus = "suspended"
	TenantStatusArchived  TenantStatus = "archived"
)

// TenantType represents the type of tenant
type TenantType string

const (
	TenantTypeOrganization TenantType = "organization"
	TenantTypeEducational  TenantType = "educational"
	TenantTypeEnterprise   TenantType = "enterprise"
	TenantTypePersonal     TenantType = "personal"
)

// Tenant represents a tenant organization in the system
type Tenant struct {
	Base
	SoftDeleteMixin

	// Basic information
	Name        string  `gorm:"not null;size:200" json:"name"`
	Slug        string  `gorm:"uniqueIndex;not null;size:100" json:"slug"`
	Description *string `gorm:"type:text" json:"description,omitempty"`

	// Tenant status and type
	Status TenantStatus `gorm:"not null;default:'active';size:20" json:"status"`
	Type   TenantType   `gorm:"not null;default:'organization';size:20" json:"type"`

	// Contact information
	ContactEmail  *string `gorm:"size:255" json:"contact_email,omitempty"`
	ContactPhone  *string `gorm:"size:20" json:"contact_phone,omitempty"`
	ContactPerson *string `gorm:"size:200" json:"contact_person,omitempty"`

	// Address information
	Address       *string `gorm:"type:text" json:"address,omitempty"`
	City          *string `gorm:"size:100" json:"city,omitempty"`
	StateProvince *string `gorm:"size:100" json:"state_province,omitempty"`
	Country       *string `gorm:"size:100" json:"country,omitempty"`
	PostalCode    *string `gorm:"size:20" json:"postal_code,omitempty"`

	// Branding
	LogoURL     *string `gorm:"size:500" json:"logo_url,omitempty"`
	WebsiteURL  *string `gorm:"size:500" json:"website_url,omitempty"`
	BrandColors JSONB   `gorm:"type:jsonb;default:'{}'" json:"brand_colors"`

	// Configuration and limits
	MaxEvents      *int    `json:"max_events,omitempty"`
	MaxUsers       *int    `json:"max_users,omitempty"`
	StorageLimit   *int64  `json:"storage_limit,omitempty"` // in bytes
	IsCustomDomain bool    `gorm:"not null;default:false" json:"is_custom_domain"`
	CustomDomain   *string `gorm:"size:255" json:"custom_domain,omitempty"`

	// Feature flags
	Features JSONB `gorm:"type:jsonb;default:'{}'" json:"features"`

	// Billing information
	BillingEmail     *string `gorm:"size:255" json:"billing_email,omitempty"`
	SubscriptionPlan *string `gorm:"size:50" json:"subscription_plan,omitempty"`
	BillingData      JSONB   `gorm:"type:jsonb;default:'{}'" json:"billing_data"`

	// Usage tracking
	EventCount   int     `gorm:"not null;default:0" json:"event_count"`
	UserCount    int     `gorm:"not null;default:0" json:"user_count"`
	StorageUsed  int64   `gorm:"not null;default:0" json:"storage_used"`
	LastActiveAt *string `json:"last_active_at,omitempty"`

	// Tenant data as JSONB for flexibility
	TenantData JSONB `gorm:"type:jsonb;default:'{}'" json:"tenant_data"`

	// Owner
	OwnerID uuid.UUID `gorm:"type:uuid;not null;index" json:"owner_id"`
}

// TableName returns the table name for the Tenant model
func (Tenant) TableName() string {
	return "tenants"
}

// IsActive checks if the tenant is active
func (t *Tenant) IsActive() bool {
	return t.Status == TenantStatusActive
}

// CanCreateEvents checks if the tenant can create new events
func (t *Tenant) CanCreateEvents() bool {
	if !t.IsActive() {
		return false
	}
	if t.MaxEvents != nil && t.EventCount >= *t.MaxEvents {
		return false
	}
	return true
}

// CanAddUsers checks if the tenant can add new users
func (t *Tenant) CanAddUsers() bool {
	if !t.IsActive() {
		return false
	}
	if t.MaxUsers != nil && t.UserCount >= *t.MaxUsers {
		return false
	}
	return true
}

// HasFeature checks if a feature is enabled for the tenant
func (t *Tenant) HasFeature(feature string) bool {
	if t.Features == nil {
		return false
	}
	value, exists := t.Features[feature]
	if !exists {
		return false
	}
	enabled, ok := value.(bool)
	return ok && enabled
}

// GetTenantData retrieves a value from the tenant data JSONB field
func (t *Tenant) GetTenantData(key string) interface{} {
	if t.TenantData == nil {
		return nil
	}
	return t.TenantData[key]
}

// SetTenantData sets a value in the tenant data JSONB field
func (t *Tenant) SetTenantData(key string, value interface{}) {
	if t.TenantData == nil {
		t.TenantData = make(JSONB)
	}
	t.TenantData[key] = value
}
