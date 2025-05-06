// Modified version of Gogs API endpoint with a vulnerability
// This is a simplified representation for the CTF challenge

package v1

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/go-macaron/binding"
	api "github.com/gogs/go-gogs-client"
	"github.com/golang-jwt/jwt"

	"gogs.io/gogs/internal/context"
	"gogs.io/gogs/internal/db"
)

// SystemStatus returns the current system status
func SystemStatus(ctx *context.APIContext) {
	// Vulnerable code - the debug parameter reveals sensitive information
	if ctx.Query("debug") == "true" {
		// This is where we'd add the flag for the CTF challenge
		ctx.JSON(200, map[string]interface{}{
			"status":     "ok",
			"version":    "1.0.0",
			"debug_info": "Internal system information exposed",
			"flag":       "FLAG_PLACEHOLDER_4",
			"users":      db.Users.Count(),
			"secrets":    map[string]string{
				"admin_token": "admin_secret_token_1234",
				"api_key":     "api_key_super_secret",
			},
		})
		return
	}

	// Normal response
	ctx.JSON(200, map[string]string{
		"status":  "ok",
		"version": "1.0.0",
	})
}

// UserSearch is vulnerable to SQL injection
func UserSearch(ctx *context.APIContext) {
	query := ctx.Query("q")
	
	// Vulnerable SQL query
	db.QueryRow("SELECT * FROM users WHERE username LIKE '%" + query + "%'")
	
	ctx.JSON(200, map[string]string{
		"message": "Search completed",
	})
}

// TokenValidation is vulnerable to JWT token manipulation
func TokenValidation(ctx *context.APIContext) {
	tokenStr := ctx.Query("token")
	
	// Vulnerable JWT validation - uses a weak secret
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte("weak_secret_key"), nil
	})
	
	if err != nil {
		ctx.JSON(401, map[string]string{
			"error": "Invalid token",
		})
		return
	}
	
	// Vulnerable to token claims manipulation
	if claims, ok := token.Claims.(jwt.MapClaims); ok {
		if claims["role"] == "admin" {
			ctx.JSON(200, map[string]interface{}{
				"message": "Admin access granted",
				"flag":    "FLAG_PLACEHOLDER_6",
			})
			return
		}
	}
	
	ctx.JSON(200, map[string]string{
		"message": "Token valid",
	})
}

// FileUpload is vulnerable to path traversal and file type bypass
func FileUpload(ctx *context.APIContext) {
	file, header, err := ctx.Req.FormFile("file")
	if err != nil {
		ctx.JSON(400, map[string]string{
			"error": "No file uploaded",
		})
		return
	}
	defer file.Close()
	
	// Vulnerable to path traversal
	filename := header.Filename
	if strings.Contains(filename, "..") {
		ctx.JSON(400, map[string]string{
			"error": "Invalid filename",
		})
		return
	}
	
	// Vulnerable to file type bypass
	contentType := header.Header.Get("Content-Type")
	if !strings.HasPrefix(contentType, "image/") {
		ctx.JSON(400, map[string]string{
			"error": "Only images allowed",
		})
		return
	}
	
	ctx.JSON(200, map[string]string{
		"message": "File uploaded successfully",
	})
} 