package main

import (
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	// Hook into the password reset email for the "users" collection.
	app.OnMailerBeforeRecordResetPasswordSend("users").Add(func(e *core.MailerRecordEvent) error {
		role := e.Record.GetString("role")

		if role != "admin" && role != "user" {
			// No modification needed for other roles.
			return nil
		}

		appName := app.Settings().Meta.AppName

		// Reconstruct the action URL by resolving the template's ActionUrl
		// with the token stored in e.Meta.
		token, _ := e.Meta["token"].(string)
		actionUrlTemplate := app.Settings().Meta.ResetPasswordTemplate.ActionUrl
		actionUrl := strings.ReplaceAll(actionUrlTemplate, "{TOKEN}", token)
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_NAME}", appName)
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_URL}", app.Settings().Meta.AppUrl)

		switch role {
		case "admin":
			e.Message.Subject = "Admin Password Reset - " + appName
			e.Message.HTML = "Admin Reset Link: " + actionUrl
		case "user":
			e.Message.Subject = "User Password Reset - " + appName
			e.Message.HTML = "User Reset Link: " + actionUrl
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
