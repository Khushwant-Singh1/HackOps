package handlers

import (
	"net/http"

	"hackops/internal/auth"
	"hackops/internal/database"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// GetCurrentUser returns the current authenticated user
func GetCurrentUser(c *gin.Context) {
	user, exists := auth.GetUserFromContext(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user": user,
	})
}

// UpdateCurrentUser updates the current user's profile
func UpdateCurrentUser(userService *UserService) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not found"})
			return
		}

		var updateData struct {
			FirstName       *string   `json:"first_name"`
			LastName        *string   `json:"last_name"`
			DisplayName     *string   `json:"display_name"`
			Bio             *string   `json:"bio"`
			PhoneNumber     *string   `json:"phone_number"`
			Country         *string   `json:"country"`
			StateProvince   *string   `json:"state_province"`
			City            *string   `json:"city"`
			Timezone        *string   `json:"timezone"`
			Skills          *[]string `json:"skills"`
			Interests       *[]string `json:"interests"`
			ExperienceLevel *string   `json:"experience_level"`
			GitHubUsername  *string   `json:"github_username"`
			LinkedInURL     *string   `json:"linkedin_url"`
			PortfolioURL    *string   `json:"portfolio_url"`
		}

		if err := c.ShouldBindJSON(&updateData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Update user in database
		if err := userService.db.Model(&database.User{}).Where("id = ?", user.ID).Updates(updateData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update user"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "User updated successfully",
		})
	}
}

// ListEvents returns a list of events
func ListEvents(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		var events []database.Event

		// Get query parameters for filtering
		tenantID := c.Query("tenant_id")
		status := c.Query("status")

		query := eventService.db.DB

		if tenantID != "" {
			query = query.Where("tenant_id = ?", tenantID)
		}

		if status != "" {
			query = query.Where("status = ?", status)
		}

		// Only get non-deleted events
		if err := query.Where("deleted_at IS NULL").Find(&events).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch events"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"events": events,
		})
	}
}

// GetEvent returns a single event by ID
func GetEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")

		var event database.Event
		if err := eventService.db.Where("id = ? AND deleted_at IS NULL", eventID).First(&event).Error; err != nil {
			if err.Error() == "record not found" {
				c.JSON(http.StatusNotFound, gin.H{"error": "Event not found"})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"event": event,
		})
	}
}

// CreateEvent creates a new event
func CreateEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		var eventData database.Event
		if err := c.ShouldBindJSON(&eventData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Set event metadata
		eventData.ID = uuid.New().String()
		eventData.OrganizerID = user.ID

		// Set default values if not provided
		if eventData.Status == "" {
			eventData.Status = "draft"
		}
		if eventData.EventType == "" {
			eventData.EventType = "in_person"
		}
		if eventData.Visibility == "" {
			eventData.Visibility = "public"
		}

		// Create the event
		if err := eventService.db.Create(&eventData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create event"})
			return
		}

		c.JSON(http.StatusCreated, gin.H{
			"message": "Event created successfully",
			"event":   eventData,
		})
	}
}

// UpdateEvent updates an existing event
func UpdateEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		var updateData database.Event
		if err := c.ShouldBindJSON(&updateData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Check if event exists and user has permission
		var existingEvent database.Event
		if err := eventService.db.Where("id = ? AND deleted_at IS NULL", eventID).First(&existingEvent).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Event not found"})
			return
		}

		// Check if user is the organizer (basic permission check)
		if existingEvent.OrganizerID != user.ID {
			c.JSON(http.StatusForbidden, gin.H{"error": "Not authorized to update this event"})
			return
		}

		// Update the event
		if err := eventService.db.Model(&existingEvent).Updates(updateData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Event updated successfully",
			"event":   existingEvent,
		})
	}
}

// DeleteEvent deletes an event
func DeleteEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		// Check if event exists and user has permission
		var event database.Event
		if err := eventService.db.Where("id = ? AND deleted_at IS NULL", eventID).First(&event).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Event not found"})
			return
		}

		if event.OrganizerID != user.ID {
			c.JSON(http.StatusForbidden, gin.H{"error": "Not authorized to delete this event"})
			return
		}

		// Soft delete the event
		if err := eventService.db.Where("id = ?", eventID).Delete(&database.Event{}).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Event deleted successfully",
		})
	}
}

// StartEvent starts an event
func StartEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		// Update event status to active
		if err := eventService.db.Model(&database.Event{}).Where("id = ? AND organizer_id = ?", eventID, user.ID).Update("status", "active").Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to start event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Event started successfully",
		})
	}
}

// CompleteEvent completes an event
func CompleteEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		// Update event status to completed
		if err := eventService.db.Model(&database.Event{}).Where("id = ? AND organizer_id = ?", eventID, user.ID).Update("status", "completed").Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to complete event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Event completed successfully",
		})
	}
}

// CancelEvent cancels an event
func CancelEvent(eventService *EventService) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventID := c.Param("id")
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		// Update event status to cancelled
		if err := eventService.db.Model(&database.Event{}).Where("id = ? AND organizer_id = ?", eventID, user.ID).Update("status", "cancelled").Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to cancel event"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Event cancelled successfully",
		})
	}
}

// Team handlers
func ListTeams(teamService *TeamService) gin.HandlerFunc {
	return func(c *gin.Context) {
		var teams []database.Team
		if err := teamService.db.Where("deleted_at IS NULL").Find(&teams).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch teams"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"teams": teams})
	}
}

func CreateTeam(teamService *TeamService) gin.HandlerFunc {
	return func(c *gin.Context) {
		var teamData database.Team
		if err := c.ShouldBindJSON(&teamData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		teamData.ID = uuid.New().String()
		if err := teamService.db.Create(&teamData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create team"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "Team created", "team": teamData})
	}
}

func GetTeam(teamService *TeamService) gin.HandlerFunc {
	return func(c *gin.Context) {
		teamID := c.Param("id")
		var team database.Team
		if err := teamService.db.Where("id = ? AND deleted_at IS NULL", teamID).First(&team).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Team not found"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"team": team})
	}
}

func UpdateTeam(teamService *TeamService) gin.HandlerFunc {
	return func(c *gin.Context) {
		teamID := c.Param("id")
		var updateData database.Team
		if err := c.ShouldBindJSON(&updateData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		if err := teamService.db.Model(&database.Team{}).Where("id = ?", teamID).Updates(updateData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update team"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "Team updated"})
	}
}

func DeleteTeam(teamService *TeamService) gin.HandlerFunc {
	return func(c *gin.Context) {
		teamID := c.Param("id")
		if err := teamService.db.Where("id = ?", teamID).Delete(&database.Team{}).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete team"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "Team deleted"})
	}
}

// Submission handlers
func ListSubmissions(db *database.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"submissions": []interface{}{}})
	}
}

func CreateSubmission(db *database.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusCreated, gin.H{"message": "Submission created"})
	}
}

func GetSubmission(db *database.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		submissionID := c.Param("id")
		c.JSON(http.StatusOK, gin.H{"submission": map[string]interface{}{}, "id": submissionID})
	}
}

func UpdateSubmission(db *database.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		submissionID := c.Param("id")
		c.JSON(http.StatusOK, gin.H{"message": "Submission updated", "id": submissionID})
	}
}

func DeleteSubmission(db *database.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		submissionID := c.Param("id")
		c.JSON(http.StatusOK, gin.H{"message": "Submission deleted", "id": submissionID})
	}
}

// Tenant handlers
func ListTenants(tenantService *TenantService) gin.HandlerFunc {
	return func(c *gin.Context) {
		var tenants []database.Tenant
		if err := tenantService.db.Where("deleted_at IS NULL").Find(&tenants).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch tenants"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"tenants": tenants})
	}
}

func CreateTenant(tenantService *TenantService) gin.HandlerFunc {
	return func(c *gin.Context) {
		var tenantData database.Tenant
		if err := c.ShouldBindJSON(&tenantData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		tenantData.ID = uuid.New().String()
		if err := tenantService.db.Create(&tenantData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create tenant"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "Tenant created", "tenant": tenantData})
	}
}

func GetTenant(tenantService *TenantService) gin.HandlerFunc {
	return func(c *gin.Context) {
		tenantID := c.Param("id")
		var tenant database.Tenant
		if err := tenantService.db.Where("id = ? AND deleted_at IS NULL", tenantID).First(&tenant).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Tenant not found"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"tenant": tenant})
	}
}

func UpdateTenant(tenantService *TenantService) gin.HandlerFunc {
	return func(c *gin.Context) {
		tenantID := c.Param("id")
		var updateData database.Tenant
		if err := c.ShouldBindJSON(&updateData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		if err := tenantService.db.Model(&database.Tenant{}).Where("id = ?", tenantID).Updates(updateData).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update tenant"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "Tenant updated"})
	}
}

func DeleteTenant(tenantService *TenantService) gin.HandlerFunc {
	return func(c *gin.Context) {
		tenantID := c.Param("id")
		if err := tenantService.db.Where("id = ?", tenantID).Delete(&database.Tenant{}).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete tenant"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "Tenant deleted"})
	}
}
