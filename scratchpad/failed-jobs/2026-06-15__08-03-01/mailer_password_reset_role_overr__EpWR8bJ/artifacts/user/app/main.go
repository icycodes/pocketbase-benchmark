package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/models/schema"
)

func main() {
	app := pocketbase.New()

	// Add the "role" text field to the "users" collection on serve
	app.OnBeforeServe().Add(func(e *core.ServeEvent) error {
		collection, err := app.Dao().FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		// Check if the "role" field already exists
		if collection.Schema.GetFieldByName("role") == nil {
			collection.Schema.AddField(&schema.SchemaField{
				System:   false,
				Id:       "users_role",
				Name:     "role",
				Type:     schema.FieldTypeText,
				Required: false,
				Options: &schema.TextOptions{
					Min: nil,
					Max: nil,
				},
			})

			if err := app.Dao().SaveCollection(collection); err != nil {
				return err
			}
		}

		return nil
	})

	// Intercept password reset emails for the "users" collection
	app.OnMailerBeforeRecordResetPasswordSend("users").Add(func(e *core.MailerRecordEvent) error {
		role := e.Record.GetString("role")

		if role != "admin" && role != "user" {
			return nil
		}

		token, ok := e.Meta["token"].(string)
		if !ok {
			return nil
		}

		// Resolve the action URL using the reset password email template
		_, _, actionUrl := app.Settings().Meta.ResetPasswordTemplate.Resolve(
			app.Settings().Meta.AppName,
			app.Settings().Meta.AppUrl,
			token,
		)

		appName := app.Settings().Meta.AppName

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