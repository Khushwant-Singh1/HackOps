package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"hackops/internal/auth"
	"hackops/internal/config"
	"hackops/internal/database"
	"hackops/internal/handlers"
	"hackops/internal/middleware"

	"github.com/gin-gonic/gin"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize database
	gormDB, err := database.NewConnection(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	db := database.NewDBWrapper(gormDB)

	// Run auto migration
	if err := db.AutoMigrate(); err != nil {
		log.Fatalf("Failed to run database migrations: %v", err)
	}
	log.Println("Database migrations completed successfully")

	// Initialize Redis client
	redisClient, err := database.NewRedisClient(cfg.RedisURL)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}

	// Initialize JWT manager
	jwtManager := auth.NewJWTManager(cfg.SecretKey, cfg.AccessTokenExpire, cfg.RefreshTokenExpire)

	// Initialize services
	userService := handlers.NewUserService(db)
	eventService := handlers.NewEventService(db)
	teamService := handlers.NewTeamService(db)
	tenantService := handlers.NewTenantService(db)

	// Setup Gin
	if cfg.Debug {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Add middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	router.Use(middleware.CORS(cfg.AllowedHosts))
	router.Use(middleware.SecurityHeaders())

	// Health check endpoints
	router.GET("/health", handlers.HealthCheck)
	router.GET("/health/detailed", handlers.DetailedHealthCheck(gormDB, redisClient))

	// Root endpoint
	router.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message":      fmt.Sprintf("Welcome to %s API", cfg.AppName),
			"version":      cfg.Version,
			"docs_url":     "/docs",
			"health_check": "/health",
		})
	})

	// API v1 routes
	v1 := router.Group("/api/v1")

	// Authentication routes
	authRoutes := v1.Group("/auth")
	{
		authRoutes.POST("/login", handlers.Login(userService, jwtManager))
		authRoutes.POST("/register", handlers.Register(userService, jwtManager))
		authRoutes.POST("/refresh", handlers.RefreshToken(jwtManager))

		// Protected routes
		protected := authRoutes.Group("/")
		protected.Use(middleware.JWTAuth(jwtManager))
		{
			protected.POST("/logout", handlers.Logout(redisClient))
			protected.POST("/logout-all", handlers.LogoutAll(redisClient))
			protected.POST("/change-password", handlers.ChangePassword(userService))
		}
	}

	// Event routes
	eventRoutes := v1.Group("/events")
	eventRoutes.Use(middleware.JWTAuth(jwtManager))
	{
		eventRoutes.GET("/", handlers.ListEvents(eventService))
		eventRoutes.POST("/", handlers.CreateEvent(eventService))
		eventRoutes.GET("/:id", handlers.GetEvent(eventService))
		eventRoutes.PUT("/:id", handlers.UpdateEvent(eventService))
		eventRoutes.DELETE("/:id", handlers.DeleteEvent(eventService))
		eventRoutes.POST("/:id/start", handlers.StartEvent(eventService))
		eventRoutes.POST("/:id/complete", handlers.CompleteEvent(eventService))
		eventRoutes.POST("/:id/cancel", handlers.CancelEvent(eventService))
	}

	// Team routes
	teamRoutes := v1.Group("/teams")
	teamRoutes.Use(middleware.JWTAuth(jwtManager))
	{
		teamRoutes.GET("/", handlers.ListTeams(teamService))
		teamRoutes.POST("/", handlers.CreateTeam(teamService))
		teamRoutes.GET("/:id", handlers.GetTeam(teamService))
		teamRoutes.PUT("/:id", handlers.UpdateTeam(teamService))
		teamRoutes.DELETE("/:id", handlers.DeleteTeam(teamService))
	}

	// Tenant routes
	tenantRoutes := v1.Group("/tenants")
	tenantRoutes.Use(middleware.JWTAuth(jwtManager))
	{
		tenantRoutes.GET("/", handlers.ListTenants(tenantService))
		tenantRoutes.POST("/", handlers.CreateTenant(tenantService))
		tenantRoutes.GET("/:id", handlers.GetTenant(tenantService))
		tenantRoutes.PUT("/:id", handlers.UpdateTenant(tenantService))
		tenantRoutes.DELETE("/:id", handlers.DeleteTenant(tenantService))
	}

	// Start server
	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.Port),
		Handler: router,
	}

	// Graceful shutdown
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, os.Interrupt, syscall.SIGTERM)
		<-sigint

		log.Println("Shutting down server...")

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		if err := server.Shutdown(ctx); err != nil {
			log.Fatalf("Server forced to shutdown: %v", err)
		}

		// Close database connection
		sqlDB, err := gormDB.DB()
		if err == nil {
			sqlDB.Close()
		}

		// Close Redis connection
		redisClient.Close()

		log.Println("Server exited")
	}()

	log.Printf("Starting %s server on port %d", cfg.AppName, cfg.Port)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Failed to start server: %v", err)
	}
}
