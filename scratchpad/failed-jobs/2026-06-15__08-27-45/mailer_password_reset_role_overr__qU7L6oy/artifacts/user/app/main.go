package main

import (
	"fmt"
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnMailerBeforeRecordResetPasswordSend("users").Add(func(e *core.MailerRecordEvent) error {
		role := e.Record.GetString("role")
		appName := app.Settings().Meta.AppName
		token := e.Meta["token"].(string)

		// Build the action URL by replacing {TOKEN} in the configured template
		actionUrl := app.Settings().Meta.ResetPasswordTemplate.ActionUrl
		actionUrl = strings.ReplaceAll(actionUrl, "{TOKEN}", token)
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_URL}", app.Settings().Meta.AppUrl)
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_NAME}", appName)

		switch role {
		case "admin":
			e.Message.Subject = fmt.Sprintf("Admin Password Reset - %s", appName)
			e.Message.HTML = fmt.Sprintf("Admin Reset Link: %s", actionUrl)
		case "user":
			e.Message.Subject = fmt.Sprintf("User Password Reset - %s", appName)
			e.Message.HTML = fmt.Sprintf("User Reset Link: %s", actionUrl)
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
