package auth

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// AuthJSUser represents the user object from Auth.js
type AuthJSUser struct {
	ID            string                 `json:"id"`
	Name          string                 `json:"name"`
	Email         string                 `json:"email"`
	Image         string                 `json:"image"`
	EmailVerified *time.Time             `json:"emailVerified"`
	Role          string                 `json:"role,omitempty"`
	TenantID      string                 `json:"tenantId,omitempty"`
	CustomClaims  map[string]interface{} `json:"customClaims,omitempty"`
}

// AuthJSSession represents the session object from Auth.js
type AuthJSSession struct {
	User        AuthJSUser `json:"user"`
	Expires     string     `json:"expires"`
	AccessToken string     `json:"accessToken,omitempty"`
}

// AuthJSVerifier handles Auth.js session verification
type AuthJSVerifier struct {
	nextJSURL  string
	secret     string
	cookieName string
	httpClient *http.Client
}

// NewAuthJSVerifier creates a new Auth.js session verifier
func NewAuthJSVerifier(nextJSURL, secret string) *AuthJSVerifier {
	return &AuthJSVerifier{
		nextJSURL:  nextJSURL,
		secret:     secret,
		cookieName: "next-auth.session-token",
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// VerifySession verifies a session token with the Next.js Auth.js endpoint
func (av *AuthJSVerifier) VerifySession(ctx context.Context, sessionToken string) (*AuthJSSession, error) {
	// Create request to Next.js API route for session verification
	url := fmt.Sprintf("%s/api/auth/session", av.nextJSURL)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add the session token as a cookie
	req.AddCookie(&http.Cookie{
		Name:  av.cookieName,
		Value: sessionToken,
	})

	// Add authorization header as well (for JWT tokens)
	if sessionToken != "" {
		req.Header.Set("Authorization", "Bearer "+sessionToken)
	}

	resp, err := av.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to verify session: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("session verification failed with status: %d", resp.StatusCode)
	}

	var session AuthJSSession
	if err := json.NewDecoder(resp.Body).Decode(&session); err != nil {
		return nil, fmt.Errorf("failed to decode session: %w", err)
	}

	return &session, nil
}

// AuthJSMiddleware creates a Gin middleware for Auth.js session verification
func AuthJSMiddleware(verifier *AuthJSVerifier) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Try to get token from different sources
		var token string

		// 1. Check Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			parts := strings.Split(authHeader, " ")
			if len(parts) == 2 && parts[0] == "Bearer" {
				token = parts[1]
			}
		}

		// 2. Check cookie
		if token == "" {
			if cookie, err := c.Cookie(verifier.cookieName); err == nil {
				token = cookie
			}
		}

		// 3. Check session cookie (alternative name)
		if token == "" {
			if cookie, err := c.Cookie("__Secure-next-auth.session-token"); err == nil {
				token = cookie
			}
		}

		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "No authentication token provided",
			})
			c.Abort()
			return
		}

		// Verify session with Next.js
		session, err := verifier.VerifySession(c.Request.Context(), token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid session",
				"details": err.Error(),
			})
			c.Abort()
			return
		}

		// Store session data in context
		c.Set("session", session)
		c.Set("user", session.User)
		c.Set("user_id", session.User.ID)
		c.Set("email", session.User.Email)
		c.Set("role", session.User.Role)
		c.Set("tenant_id", session.User.TenantID)

		c.Next()
	}
}

// OptionalAuthJSMiddleware creates a middleware that doesn't require authentication but adds user info if available
func OptionalAuthJSMiddleware(verifier *AuthJSVerifier) gin.HandlerFunc {
	return func(c *gin.Context) {
		var token string

		// Try to get token from different sources
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			parts := strings.Split(authHeader, " ")
			if len(parts) == 2 && parts[0] == "Bearer" {
				token = parts[1]
			}
		}

		if token == "" {
			if cookie, err := c.Cookie(verifier.cookieName); err == nil {
				token = cookie
			}
		}

		if token != "" {
			if session, err := verifier.VerifySession(c.Request.Context(), token); err == nil {
				c.Set("session", session)
				c.Set("user", session.User)
				c.Set("user_id", session.User.ID)
				c.Set("email", session.User.Email)
				c.Set("role", session.User.Role)
				c.Set("tenant_id", session.User.TenantID)
			}
		}

		c.Next()
	}
}

// GetUserFromContext extracts user information from Gin context
func GetUserFromContext(c *gin.Context) (*AuthJSUser, bool) {
	if user, exists := c.Get("user"); exists {
		if authUser, ok := user.(AuthJSUser); ok {
			return &authUser, true
		}
	}
	return nil, false
}

// GetSessionFromContext extracts session information from Gin context
func GetSessionFromContext(c *gin.Context) (*AuthJSSession, bool) {
	if session, exists := c.Get("session"); exists {
		if authSession, ok := session.(*AuthJSSession); ok {
			return authSession, true
		}
	}
	return nil, false
}

// RequireAuth ensures the user is authenticated
func RequireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		if _, exists := GetUserFromContext(c); !exists {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// RequireRole ensures the user has a specific role
func RequireRole(role string) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, exists := GetUserFromContext(c)
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required",
			})
			c.Abort()
			return
		}

		if user.Role != role {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Insufficient permissions",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}
