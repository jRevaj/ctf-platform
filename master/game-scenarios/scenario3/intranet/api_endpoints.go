// Modified version of Gogs API endpoint with a vulnerability
// This is a simplified representation for the CTF challenge

package v1

import (
	"net/http"

	"github.com/go-macaron/binding"
	api "github.com/gogs/go-gogs-client"

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