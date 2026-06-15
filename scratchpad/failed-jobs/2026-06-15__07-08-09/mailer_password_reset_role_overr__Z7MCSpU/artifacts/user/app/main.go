package main

import (
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnMailerBeforeRecordResetPasswordSend("users").Add(func(e *core.MailerRecordEvent) error {
		role := e.Record.GetString("role")
		if role != "admin" && role != "user" {
			return nil
		}

		appName := app.Settings().Meta.AppName
		appUrl := app.Settings().Meta.AppUrl
		token, _ := e.Meta["token"].(string)
		baseActionUrl := app.Settings().Meta.ResetPasswordTemplate.ActionUrl

		// Construct ACTION_URL
		actionUrl := baseActionUrl
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_URL}", appUrl)
		actionUrl = strings.ReplaceAll(actionUrl, "{TOKEN}", token)
		actionUrl = strings.ReplaceAll(actionUrl, "{APP_NAME}", appName)

		if role == "admin" {
			e.Message.Subject = "Admin Password Reset - " + appName
			e.Message.HTML = "Admin Reset Link: " + actionUrl
		} else if role == "user" {
			e.Message.Subject = "User Password Reset - " + appName
			e.Message.HTML = "User Reset Link: " + actionUrl
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
