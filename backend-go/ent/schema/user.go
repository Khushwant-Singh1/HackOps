package schema

import (
	"time"

	"entgo.io/ent"
	"entgo.io/ent/dialect/entsql"
	"entgo.io/ent/schema/edge"
	"entgo.io/ent/schema/field"
	"entgo.io/ent/schema/index"
	"entgo.io/ent/schema/mixin"
	"github.com/google/uuid"
)

// TimeMixin implements the ent.Mixin for sharing
// time fields with package schemas.
type TimeMixin struct {
	mixin.Schema
}

// Fields of the TimeMixin.
func (TimeMixin) Fields() []ent.Field {
	return []ent.Field{
		field.Time("created_at").
			Default(time.Now).
			Immutable().
			Annotations(entsql.Annotation{
				Default: "CURRENT_TIMESTAMP",
			}),
		field.Time("updated_at").
			Default(time.Now).
			UpdateDefault(time.Now).
			Annotations(entsql.Annotation{
				Default: "CURRENT_TIMESTAMP",
			}),
	}
}

// User holds the schema definition for the User entity.
type User struct {
	ent.Schema
}

// Mixin of the User.
func (User) Mixin() []ent.Mixin {
	return []ent.Mixin{
		TimeMixin{},
	}
}

// Fields of the User.
func (User) Fields() []ent.Field {
	return []ent.Field{
		field.UUID("id", uuid.UUID{}).
			Default(uuid.New).
			StorageKey("id"),

		// Authentication fields
		field.String("email").
			Unique().
			NotEmpty().
			MaxLen(255),
		field.String("password_hash").
			Optional().
			Sensitive().
			MaxLen(255),
		field.Bool("is_active").
			Default(true),
		field.Bool("is_verified").
			Default(false),

		// OAuth provider information
		field.String("auth_provider").
			Optional().
			MaxLen(50),
		field.String("oauth_id").
			Optional().
			MaxLen(255),

		// System-level roles
		field.String("system_role").
			Optional().
			MaxLen(50),

		// Profile information
		field.String("first_name").
			NotEmpty().
			MaxLen(100),
		field.String("last_name").
			NotEmpty().
			MaxLen(100),
		field.String("display_name").
			Optional().
			MaxLen(200),
		field.String("avatar_url").
			Optional().
			MaxLen(500),
		field.Text("bio").
			Optional(),

		// Personal information
		field.String("phone_number").
			Optional().
			MaxLen(20),
		field.Time("date_of_birth").
			Optional(),
		field.Bool("minor_flag").
			Default(false),

		// Location
		field.String("country").
			Optional().
			MaxLen(100),
		field.String("state_province").
			Optional().
			MaxLen(100),
		field.String("city").
			Optional().
			MaxLen(100),
		field.String("timezone").
			Default("UTC").
			MaxLen(50),

		// Skills and interests (JSON arrays)
		field.JSON("skills", []string{}).
			Default([]string{}),
		field.JSON("interests", []string{}).
			Default([]string{}),
		field.String("experience_level").
			Optional().
			MaxLen(20),

		// Social links
		field.String("github_username").
			Optional().
			MaxLen(100),
		field.String("linkedin_url").
			Optional().
			MaxLen(500),
		field.String("portfolio_url").
			Optional().
			MaxLen(500),

		// GDPR and consent management
		field.Time("gdpr_consent_at").
			Optional(),
		field.Bool("marketing_consent").
			Default(false),
		field.Bool("data_processing_consent").
			Default(false),

		// Profile data as JSON for flexibility
		field.JSON("profile_data", map[string]interface{}{}).
			Default(map[string]interface{}{}),

		// Preferences and settings
		field.JSON("preferences", map[string]interface{}{}).
			Default(map[string]interface{}{}),

		// Activity tracking
		field.Time("last_login_at").
			Optional(),
		field.Int("login_count").
			Default(0),

		// Email verification
		field.String("email_verification_token").
			Optional().
			Sensitive().
			MaxLen(255),
		field.Time("email_verified_at").
			Optional(),

		// Password reset
		field.String("password_reset_token").
			Optional().
			Sensitive().
			MaxLen(255),
		field.Time("password_reset_expires_at").
			Optional(),

		// Soft delete
		field.Time("deleted_at").
			Optional(),
	}
}

// Edges of the User.
func (User) Edges() []ent.Edge {
	return []ent.Edge{
		edge.To("sessions", UserSession.Type),
		// TODO: Uncomment these edges once the corresponding ent schema files are created:
		// - ent/schema/tenant.go for Tenant entity
		// - ent/schema/event.go for Event entity
		// - ent/schema/team.go for Team entity
		// - ent/schema/submission.go for Submission entity
		//
		// edge.To("owned_tenants", Tenant.Type),
		// edge.To("events", Event.Type),
		// edge.To("teams", Team.Type),
		// edge.To("submissions", Submission.Type),
	}
}

// Indexes of the User.
func (User) Indexes() []ent.Index {
	return []ent.Index{
		index.Fields("email").Unique(),
		index.Fields("oauth_id", "auth_provider"),
		index.Fields("deleted_at"),
	}
}
