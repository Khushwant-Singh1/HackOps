package schema

import (
	"entgo.io/ent"
	"entgo.io/ent/schema/edge"
	"entgo.io/ent/schema/field"
	"entgo.io/ent/schema/index"
	"github.com/google/uuid"
)

// UserSession holds the schema definition for the UserSession entity.
type UserSession struct {
	ent.Schema
}

// Mixin of the UserSession.
func (UserSession) Mixin() []ent.Mixin {
	return []ent.Mixin{
		TimeMixin{},
	}
}

// Fields of the UserSession.
func (UserSession) Fields() []ent.Field {
	return []ent.Field{
		field.UUID("id", uuid.UUID{}).
			Default(uuid.New),
		field.UUID("user_id", uuid.UUID{}),
		field.String("session_token").
			Unique().
			MaxLen(255),
		field.String("refresh_token").
			Optional().
			Unique().
			MaxLen(255),
		field.Time("expires_at"),
		field.Bool("is_active").
			Default(true),
		field.String("ip_address").
			Optional().
			MaxLen(45),
		field.Text("user_agent").
			Optional(),
		field.JSON("device_info", map[string]interface{}{}).
			Default(map[string]interface{}{}),
	}
}

// Edges of the UserSession.
func (UserSession) Edges() []ent.Edge {
	return []ent.Edge{
		edge.From("user", User.Type).
			Ref("sessions").
			Field("user_id").
			Unique().
			Required(),
	}
}

// Indexes of the UserSession.
func (UserSession) Indexes() []ent.Index {
	return []ent.Index{
		index.Fields("session_token").Unique(),
		index.Fields("refresh_token").Unique(),
		index.Fields("user_id"),
	}
}
