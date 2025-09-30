package handlers
package handlers

import (
	"net/http"

	"hackops/internal/database"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"
)

// HealthCheck returns a basic health check
func HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "HackOps",
	})
}

// DetailedHealthCheck returns a detailed health check including database connectivity
func DetailedHealthCheck(db *gorm.DB, redisClient *redis.Client) gin.HandlerFunc {
	return func(c *gin.Context) {
		response := gin.H{
			"status":     "healthy",
			"service":    "HackOps",
			"version":    "1.0.0",
			"debug_mode": true, // This should come from config
		}

		// Check database health
		if err := database.HealthCheck(db); err != nil {
			response["status"] = "unhealthy"
			response["database"] = gin.H{
				"status": "unhealthy",
				"error":  err.Error(),
			}
			c.JSON(http.StatusServiceUnavailable, response)
			return
		}
		response["database"] = gin.H{"status": "healthy"}

		// Check Redis health
		if err := database.RedisHealthCheck(redisClient); err != nil {
			response["status"] = "degraded"
			response["redis"] = gin.H{
				"status": "unhealthy",
				"error":  err.Error(),
			}
		} else {
			response["redis"] = gin.H{"status": "healthy"}
		}

		c.JSON(http.StatusOK, response)
	}
}