package auth

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// Claims represents JWT claims
type Claims struct {
	UserID   uuid.UUID `json:"user_id"`
	Email    string    `json:"email"`
	TenantID uuid.UUID `json:"tenant_id"`
	Role     string    `json:"role"`
	jwt.RegisteredClaims
}

// JWTManager handles JWT token operations
type JWTManager struct {
	secretKey          string
	accessTokenExpiry  time.Duration
	refreshTokenExpiry time.Duration
}

// NewJWTManager creates a new JWT manager
func NewJWTManager(secretKey string, accessTokenExpiry, refreshTokenExpiry time.Duration) *JWTManager {
	return &JWTManager{
		secretKey:          secretKey,
		accessTokenExpiry:  accessTokenExpiry,
		refreshTokenExpiry: refreshTokenExpiry,
	}
}

// GenerateTokens generates access and refresh tokens
func (jm *JWTManager) GenerateTokens(userID uuid.UUID, email string, tenantID uuid.UUID, role string) (accessToken, refreshToken string, err error) {
	// Generate access token
	accessToken, err = jm.generateToken(userID, email, tenantID, role, jm.accessTokenExpiry)
	if err != nil {
		return "", "", err
	}

	// Generate refresh token (longer expiry)
	refreshToken, err = jm.generateToken(userID, email, tenantID, role, jm.refreshTokenExpiry)
	if err != nil {
		return "", "", err
	}

	return accessToken, refreshToken, nil
}

// generateToken generates a JWT token
func (jm *JWTManager) generateToken(userID uuid.UUID, email string, tenantID uuid.UUID, role string, expiry time.Duration) (string, error) {
	claims := &Claims{
		UserID:   userID,
		Email:    email,
		TenantID: tenantID,
		Role:     role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(expiry)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
			Issuer:    "hackops",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(jm.secretKey))
}

// ValidateToken validates a JWT token and returns the claims
func (jm *JWTManager) ValidateToken(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("invalid signing method")
		}
		return []byte(jm.secretKey), nil
	})

	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*Claims); ok && token.Valid {
		return claims, nil
	}

	return nil, errors.New("invalid token")
}

// RefreshToken validates a refresh token and generates new tokens
func (jm *JWTManager) RefreshToken(refreshToken string) (accessToken, newRefreshToken string, err error) {
	claims, err := jm.ValidateToken(refreshToken)
	if err != nil {
		return "", "", err
	}

	// Generate new tokens
	return jm.GenerateTokens(claims.UserID, claims.Email, claims.TenantID, claims.Role)
}
