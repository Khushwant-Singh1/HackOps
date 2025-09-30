package services

import (
	"hackops/internal/models"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// UserService handles user-related operations
type UserService struct {
	db *gorm.DB
}

// NewUserService creates a new user service
func NewUserService(db *gorm.DB) *UserService {
	return &UserService{db: db}
}

// CreateUser creates a new user
func (s *UserService) CreateUser(user *models.User) error {
	return s.db.Create(user).Error
}

// GetUserByEmail retrieves a user by email
func (s *UserService) GetUserByEmail(email string) (*models.User, error) {
	var user models.User
	err := s.db.Where("email = ?", email).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

// GetUserByID retrieves a user by ID
func (s *UserService) GetUserByID(id uuid.UUID) (*models.User, error) {
	var user models.User
	err := s.db.Where("id = ?", id).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

// UpdateUser updates a user
func (s *UserService) UpdateUser(user *models.User) error {
	return s.db.Save(user).Error
}

// DeleteUser soft deletes a user
func (s *UserService) DeleteUser(id uuid.UUID) error {
	return s.db.Delete(&models.User{}, id).Error
}

// EventService handles event-related operations
type EventService struct {
	db *gorm.DB
}

// NewEventService creates a new event service
func NewEventService(db *gorm.DB) *EventService {
	return &EventService{db: db}
}

// CreateEvent creates a new event
func (s *EventService) CreateEvent(event *models.Event) error {
	return s.db.Create(event).Error
}

// GetEventByID retrieves an event by ID
func (s *EventService) GetEventByID(id uuid.UUID) (*models.Event, error) {
	var event models.Event
	err := s.db.Where("id = ?", id).First(&event).Error
	if err != nil {
		return nil, err
	}
	return &event, nil
}

// ListEvents retrieves events with pagination
func (s *EventService) ListEvents(tenantID uuid.UUID, offset, limit int) ([]models.Event, error) {
	var events []models.Event
	err := s.db.Where("tenant_id = ?", tenantID).
		Offset(offset).
		Limit(limit).
		Find(&events).Error
	return events, err
}

// UpdateEvent updates an event
func (s *EventService) UpdateEvent(event *models.Event) error {
	return s.db.Save(event).Error
}

// DeleteEvent soft deletes an event
func (s *EventService) DeleteEvent(id uuid.UUID) error {
	return s.db.Delete(&models.Event{}, id).Error
}

// TeamService handles team-related operations
type TeamService struct {
	db *gorm.DB
}

// NewTeamService creates a new team service
func NewTeamService(db *gorm.DB) *TeamService {
	return &TeamService{db: db}
}

// CreateTeam creates a new team
func (s *TeamService) CreateTeam(team *models.Team) error {
	return s.db.Create(team).Error
}

// GetTeamByID retrieves a team by ID
func (s *TeamService) GetTeamByID(id uuid.UUID) (*models.Team, error) {
	var team models.Team
	err := s.db.Where("id = ?", id).First(&team).Error
	if err != nil {
		return nil, err
	}
	return &team, nil
}

// ListTeams retrieves teams with pagination
func (s *TeamService) ListTeams(tenantID uuid.UUID, offset, limit int) ([]models.Team, error) {
	var teams []models.Team
	err := s.db.Where("tenant_id = ?", tenantID).
		Offset(offset).
		Limit(limit).
		Find(&teams).Error
	return teams, err
}

// UpdateTeam updates a team
func (s *TeamService) UpdateTeam(team *models.Team) error {
	return s.db.Save(team).Error
}

// DeleteTeam soft deletes a team
func (s *TeamService) DeleteTeam(id uuid.UUID) error {
	return s.db.Delete(&models.Team{}, id).Error
}

// TenantService handles tenant-related operations
type TenantService struct {
	db *gorm.DB
}

// NewTenantService creates a new tenant service
func NewTenantService(db *gorm.DB) *TenantService {
	return &TenantService{db: db}
}

// CreateTenant creates a new tenant
func (s *TenantService) CreateTenant(tenant *models.Tenant) error {
	return s.db.Create(tenant).Error
}

// GetTenantByID retrieves a tenant by ID
func (s *TenantService) GetTenantByID(id uuid.UUID) (*models.Tenant, error) {
	var tenant models.Tenant
	err := s.db.Where("id = ?", id).First(&tenant).Error
	if err != nil {
		return nil, err
	}
	return &tenant, nil
}

// ListTenants retrieves tenants with pagination
func (s *TenantService) ListTenants(offset, limit int) ([]models.Tenant, error) {
	var tenants []models.Tenant
	err := s.db.Offset(offset).Limit(limit).Find(&tenants).Error
	return tenants, err
}

// UpdateTenant updates a tenant
func (s *TenantService) UpdateTenant(tenant *models.Tenant) error {
	return s.db.Save(tenant).Error
}

// DeleteTenant soft deletes a tenant
func (s *TenantService) DeleteTenant(id uuid.UUID) error {
	return s.db.Delete(&models.Tenant{}, id).Error
}
