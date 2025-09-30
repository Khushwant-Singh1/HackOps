package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Base contains common columns for all tables
type Base struct {
	ID        uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	CreatedAt time.Time `gorm:"not null;default:CURRENT_TIMESTAMP" json:"created_at"`
	UpdatedAt time.Time `gorm:"not null;default:CURRENT_TIMESTAMP" json:"updated_at"`
}

// BeforeCreate will set a UUID rather than numeric ID
func (base *Base) BeforeCreate(db *gorm.DB) error {
	if base.ID == uuid.Nil {
		base.ID = uuid.New()
	}
	return nil
}

// SoftDeleteMixin provides soft delete functionality
type SoftDeleteMixin struct {
	DeletedAt *time.Time `gorm:"index" json:"deleted_at,omitempty"`
}

// TenantMixin provides multi-tenant functionality
type TenantMixin struct {
	TenantID uuid.UUID `gorm:"type:uuid;not null;index" json:"tenant_id"`
}
