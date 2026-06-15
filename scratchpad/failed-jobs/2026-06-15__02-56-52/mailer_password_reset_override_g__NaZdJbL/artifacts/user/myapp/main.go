package main

import (
	"fmt"
	"log"
	"os"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		// Ensure SMTP is configured
		app.Settings().SMTP.Enabled = true
		app.Settings().SMTP.Host = "localhost"
		app.Settings().SMTP.Port = 1025

		// Seed the user
		email := os.Getenv("TEST_USER_EMAIL")
		if email == "" {
			email = "alice@example.com"
		}
		name := os.Getenv("TEST_USER_NAME")
		if name == "" {
			name = "Alice"
		}

		collection, err := app.FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		user, err := app.FindAuthRecordByEmail("users", email)
		if err != nil || user == nil {
			// Create the user
			user = core.NewRecord(collection)
			user.Set("email", email)
			user.Set("name", name)
			user.Set("password", "password123456")
			user.Set("passwordConfirm", "password123456")
			user.Set("verified", true)
			if err := app.Save(user); err != nil {
				return fmt.Errorf("failed to save user: %w", err)
			}
		}

		return se.Next()
	})

	app.OnMailerRecordPasswordResetSend().BindFunc(func(e *core.MailerRecordEvent) error {
		e.Message.Subject = "Reset your acme.com password"
		
		name := e.Record.GetString("name")
		if name == "" {
			name = e.Record.GetString("email")
		}

		token, ok := e.Meta["token"].(string)
		if !ok {
			return fmt.Errorf("token not found in meta")
		}

		link := fmt.Sprintf("https://acme.com/reset?token=%s", token)
		e.Message.HTML = fmt.Sprintf("Hi %s! Use this link: %s", name, link)

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
