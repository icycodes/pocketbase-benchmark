package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnMailerBeforeRecordResetPasswordSend().Add(func(e *core.MailerRecordEvent) error {
		if e.Collection.Name != "users" {
			return nil
		}

		role := e.Record.GetString("role")
		if role != "admin" && role != "user" {
			return nil
		}

		token, ok := e.Meta["token"].(string)
		if !ok {
			return nil
		}

		appName := app.Settings().Meta.AppName
		appUrl := app.Settings().Meta.AppUrl
		_, _, actionUrl := app.Settings().Meta.ResetPasswordTemplate.Resolve(appName, appUrl, token)

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
