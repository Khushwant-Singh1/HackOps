package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// Config holds all configuration for the application
type Config struct {
	// Application settings
	AppName string `mapstructure:"APP_NAME"`
	Debug   bool   `mapstructure:"DEBUG"`
	Version string `mapstructure:"VERSION"`
	Port    int    `mapstructure:"PORT"`

	// Security settings
	SecretKey          string        `mapstructure:"SECRET_KEY"`
	Algorithm          string        `mapstructure:"ALGORITHM"`
	AccessTokenExpire  time.Duration `mapstructure:"ACCESS_TOKEN_EXPIRE_MINUTES"`
	RefreshTokenExpire time.Duration `mapstructure:"REFRESH_TOKEN_EXPIRE_DAYS"`

	// Database settings
	DatabaseURL         string `mapstructure:"DATABASE_URL"`
	DatabasePoolSize    int    `mapstructure:"DATABASE_POOL_SIZE"`
	DatabaseMaxOverflow int    `mapstructure:"DATABASE_MAX_OVERFLOW"`

	// Redis settings
	RedisURL string `mapstructure:"REDIS_URL"`

	// Celery settings (for background tasks)
	CeleryBrokerURL     string `mapstructure:"CELERY_BROKER_URL"`
	CeleryResultBackend string `mapstructure:"CELERY_RESULT_BACKEND"`

	// CORS settings
	AllowedHosts []string `mapstructure:"ALLOWED_HOSTS"`

	// OAuth settings
	BaseURL               string `mapstructure:"BASE_URL"`
	GoogleClientID        string `mapstructure:"GOOGLE_CLIENT_ID"`
	GoogleClientSecret    string `mapstructure:"GOOGLE_CLIENT_SECRET"`
	GitHubClientID        string `mapstructure:"GITHUB_CLIENT_ID"`
	GitHubClientSecret    string `mapstructure:"GITHUB_CLIENT_SECRET"`
	MicrosoftClientID     string `mapstructure:"MICROSOFT_CLIENT_ID"`
	MicrosoftClientSecret string `mapstructure:"MICROSOFT_CLIENT_SECRET"`

	// File storage settings
	S3Bucket           string `mapstructure:"S3_BUCKET"`
	S3Region           string `mapstructure:"S3_REGION"`
	AWSAccessKeyID     string `mapstructure:"AWS_ACCESS_KEY_ID"`
	AWSSecretAccessKey string `mapstructure:"AWS_SECRET_ACCESS_KEY"`

	// Communication services
	SendGridAPIKey   string `mapstructure:"SENDGRID_API_KEY"`
	TwilioAccountSID string `mapstructure:"TWILIO_ACCOUNT_SID"`
	TwilioAuthToken  string `mapstructure:"TWILIO_AUTH_TOKEN"`

	// Monitoring
	SentryDSN string `mapstructure:"SENTRY_DSN"`
}

// Load loads configuration from environment variables and .env file
func Load() (*Config, error) {
	viper.SetConfigFile(".env")
	viper.AutomaticEnv()

	// Set defaults
	viper.SetDefault("APP_NAME", "HackOps")
	viper.SetDefault("DEBUG", false)
	viper.SetDefault("VERSION", "1.0.0")
	viper.SetDefault("PORT", 8000)
	viper.SetDefault("ALGORITHM", "HS256")
	viper.SetDefault("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
	viper.SetDefault("REFRESH_TOKEN_EXPIRE_DAYS", 7)
	viper.SetDefault("DATABASE_POOL_SIZE", 10)
	viper.SetDefault("DATABASE_MAX_OVERFLOW", 20)
	viper.SetDefault("REDIS_URL", "redis://localhost:6379/0")
	viper.SetDefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
	viper.SetDefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
	viper.SetDefault("ALLOWED_HOSTS", "*")
	viper.SetDefault("BASE_URL", "http://localhost:8000")
	viper.SetDefault("S3_REGION", "us-east-1")

	// Try to read config file
	if err := viper.ReadInConfig(); err != nil {
		// It's okay if config file doesn't exist, we'll use env vars and defaults
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("error reading config file: %w", err)
		}
	}

	var config Config
	if err := viper.Unmarshal(&config); err != nil {
		return nil, fmt.Errorf("error unmarshaling config: %w", err)
	}

	// Convert duration fields
	config.AccessTokenExpire = time.Duration(viper.GetInt("ACCESS_TOKEN_EXPIRE_MINUTES")) * time.Minute
	config.RefreshTokenExpire = time.Duration(viper.GetInt("REFRESH_TOKEN_EXPIRE_DAYS")) * 24 * time.Hour

	// Parse allowed hosts
	allowedHostsStr := viper.GetString("ALLOWED_HOSTS")
	if allowedHostsStr != "" {
		config.AllowedHosts = strings.Split(allowedHostsStr, ",")
		for i, host := range config.AllowedHosts {
			config.AllowedHosts[i] = strings.TrimSpace(host)
		}
	}

	// Validate required fields
	if err := config.validate(); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	return &config, nil
}

// validate checks that required configuration values are set
func (c *Config) validate() error {
	if c.SecretKey == "" {
		return fmt.Errorf("SECRET_KEY is required")
	}

	if c.DatabaseURL == "" {
		return fmt.Errorf("DATABASE_URL is required")
	}

	return nil
}

// IsDevelopment returns true if the application is running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Debug
}

// IsProduction returns true if the application is running in production mode
func (c *Config) IsProduction() bool {
	return !c.Debug
}
