package handlers

import (
	"net/http"
	"time"

	"hackops/internal/auth"
	"hackops/internal/database"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

// UserService represents the user service
type UserService struct {
	db *database.DB
}

// NewUserService creates a new user service
func NewUserService(db *database.DB) *UserService {
	return &UserService{db: db}
}

// EventService represents the event service
type EventService struct {
	db *database.DB
}

// NewEventService creates a new event service
func NewEventService(db *database.DB) *EventService {
	return &EventService{db: db}
}

// TeamService represents the team service
type TeamService struct {
	db *database.DB
}

// NewTeamService creates a new team service
func NewTeamService(db *database.DB) *TeamService {
	return &TeamService{db: db}
}

// TenantService represents the tenant service
type TenantService struct {
	db *database.DB
}

// NewTenantService creates a new tenant service
func NewTenantService(db *database.DB) *TenantService {
	return &TenantService{db: db}
}

// Login handles user login
func Login(userService *UserService, jwtManager *auth.JWTManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var loginData struct {
			Email    string `json:"email" binding:"required,email"`
			Password string `json:"password" binding:"required"`
		}

		if err := c.ShouldBindJSON(&loginData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Find user by email
		var user database.User
		if err := userService.db.Where("email = ? AND deleted_at IS NULL", loginData.Email).First(&user).Error; err != nil {
			if err == gorm.ErrRecordNotFound {
				c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		// Check password
		if user.PasswordHash == nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
			return
		}

		if err := bcrypt.CompareHashAndPassword([]byte(*user.PasswordHash), []byte(loginData.Password)); err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
			return
		}

		// Update login tracking
		now := time.Now()
		userService.db.Model(&user).Updates(map[string]interface{}{
			"last_login_at": &now,
			"login_count":   gorm.Expr("login_count + 1"),
		})

		// Generate tokens
		accessToken, refreshToken, err := jwtManager.GenerateTokens(
			func() uuid.UUID {
				if id, err := uuid.Parse(user.ID); err == nil {
					return id
				}
				return uuid.New()
			}(),
			user.Email,
			uuid.New(), // Default tenant ID for now
			"user",     // Default role
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate tokens"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"access_token":  accessToken,
			"refresh_token": refreshToken,
			"user": gin.H{
				"id":           user.ID,
				"email":        user.Email,
				"first_name":   user.FirstName,
				"last_name":    user.LastName,
				"display_name": user.DisplayName,
			},
		})
	}
}

// Register handles user registration
func Register(userService *UserService, jwtManager *auth.JWTManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var registerData struct {
			Email     string `json:"email" binding:"required,email"`
			Password  string `json:"password" binding:"required,min=8"`
			FirstName string `json:"first_name" binding:"required"`
			LastName  string `json:"last_name" binding:"required"`
		}

		if err := c.ShouldBindJSON(&registerData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Check if user already exists
		var existingUser database.User
		if err := userService.db.Where("email = ?", registerData.Email).First(&existingUser).Error; err == nil {
			c.JSON(http.StatusConflict, gin.H{"error": "User with this email already exists"})
			return
		}

		// Hash password
		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(registerData.Password), bcrypt.DefaultCost)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
			return
		}

		// Create user
		user := database.User{
			ID:           uuid.New().String(),
			Email:        registerData.Email,
			PasswordHash: func(s string) *string { return &s }(string(hashedPassword)),
			FirstName:    registerData.FirstName,
			LastName:     registerData.LastName,
			DisplayName:  func(s string) *string { return &s }(registerData.FirstName + " " + registerData.LastName),
			IsActive:     true,
			IsVerified:   false, // Set to false, user needs to verify email
		}

		if err := userService.db.Create(&user).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
			return
		}

		// Generate tokens
		userUUID, _ := uuid.Parse(user.ID)
		accessToken, refreshToken, err := jwtManager.GenerateTokens(
			userUUID,
			user.Email,
			uuid.New(), // Default tenant ID for now
			"user",     // Default role
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate tokens"})
			return
		}

		c.JSON(http.StatusCreated, gin.H{
			"message":       "User registered successfully",
			"access_token":  accessToken,
			"refresh_token": refreshToken,
			"user": gin.H{
				"id":           user.ID,
				"email":        user.Email,
				"first_name":   user.FirstName,
				"last_name":    user.LastName,
				"display_name": user.DisplayName,
			},
		})
	}
}

// RefreshToken handles token refresh
func RefreshToken(jwtManager *auth.JWTManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var tokenData struct {
			RefreshToken string `json:"refresh_token" binding:"required"`
		}

		if err := c.ShouldBindJSON(&tokenData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Validate refresh token and generate new tokens
		accessToken, newRefreshToken, err := jwtManager.RefreshToken(tokenData.RefreshToken)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid refresh token"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"access_token":  accessToken,
			"refresh_token": newRefreshToken,
		})
	}
}

// Logout handles user logout
func Logout(redisClient interface{}) gin.HandlerFunc {
	return func(c *gin.Context) {
		// TODO: Implement token blacklisting in Redis
		c.JSON(http.StatusOK, gin.H{"message": "Logged out successfully"})
	}
}

// LogoutAll handles logging out from all devices
func LogoutAll(redisClient interface{}) gin.HandlerFunc {
	return func(c *gin.Context) {
		// TODO: Implement token blacklisting for all user tokens in Redis
		c.JSON(http.StatusOK, gin.H{"message": "Logged out from all devices"})
	}
}

// ChangePassword handles password change
func ChangePassword(userService *UserService) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, exists := auth.GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not found"})
			return
		}

		var passwordData struct {
			CurrentPassword string `json:"current_password" binding:"required"`
			NewPassword     string `json:"new_password" binding:"required,min=8"`
		}

		if err := c.ShouldBindJSON(&passwordData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Get current user from database
		var dbUser database.User
		if err := userService.db.Where("id = ?", user.ID).First(&dbUser).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "User not found"})
			return
		}

		// Verify current password
		if dbUser.PasswordHash == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "No password set"})
			return
		}

		if err := bcrypt.CompareHashAndPassword([]byte(*dbUser.PasswordHash), []byte(passwordData.CurrentPassword)); err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Current password is incorrect"})
			return
		}

		// Hash new password
		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(passwordData.NewPassword), bcrypt.DefaultCost)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
			return
		}

		// Update password
		newHashedPassword := string(hashedPassword)
		if err := userService.db.Model(&dbUser).Update("password_hash", &newHashedPassword).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update password"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "Password changed successfully"})
	}
}
