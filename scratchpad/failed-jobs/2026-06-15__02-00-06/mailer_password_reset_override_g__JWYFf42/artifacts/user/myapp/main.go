package main

import (
	"log"
	"os"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	// 1. Intercept password-reset email to customize subject and HTML body
	app.OnMailerRecordPasswordResetSend("users").BindFunc(func(e *core.MailerRecordEvent) error {
		// Subject must be exactly "Reset your acme.com password"
		e.Message.Subject = "Reset your acme.com password"

		// Get the user's name or fallback to email
		name := e.Record.GetString("name")
		if name == "" {
			name = e.Record.Email()
		}

		// Get the token from event meta
		token := ""
		if t, ok := e.Meta["token"].(string); ok {
			token = t
		}

		link := "https://acme.com/reset?token=" + token

		// HTML body must be exactly of the form "Hi <NAME>! Use this link: <LINK>"
		e.Message.HTML = "Hi " + name + "! Use this link: " + link
		e.Message.Text = "Hi " + name + "! Use this link: " + link

		log.Printf("Intercepted password reset email for %s. Token: %s. Link: %s", name, token, link)

		return e.Next()
	})

	// 2. Configure SMTP and seed the test user on startup
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// Configure SMTP to deliver to local Mailpit (localhost:1025)
		settings := e.App.Settings()
		settings.SMTP.Enabled = true
		settings.SMTP.Host = "localhost"
		settings.SMTP.Port = 1025
		settings.SMTP.Username = ""
		settings.SMTP.Password = ""
		settings.SMTP.TLS = false
		settings.Meta.SenderName = "Acme"
		settings.Meta.SenderAddress = "noreply@acme.com"

		if err := e.App.Save(settings); err != nil {
			log.Printf("Failed to save SMTP settings: %v", err)
			return err
		}
		log.Println("SMTP settings successfully saved and configured for localhost:1025")

		// Seed the test user
		users, err := e.App.FindCollectionByNameOrId("users")
		if err != nil {
			log.Printf("Failed to find 'users' collection: %v", err)
			return err
		}

		email := os.Getenv("TEST_USER_EMAIL")
		if email == "" {
			email = "alice@example.com"
		}
		name := os.Getenv("TEST_USER_NAME")
		if name == "" {
			name = "Alice"
		}

		record, err := e.App.FindAuthRecordByEmail("users", email)
		if err != nil {
			log.Printf("Test user %s not found, seeding a new one...", email)
			record = core.NewRecord(users)
			record.SetEmail(email)
			record.Set("name", name)
			record.SetVerified(true)
			record.Set("password", "some-secure-password-123456")
			if err := e.App.Save(record); err != nil {
				log.Printf("Failed to save seeded user: %v", err)
				return err
			}
			log.Printf("Successfully seeded test user %s with name %s", email, name)
		} else {
			log.Printf("Test user %s already exists, updating verified state and name...", email)
			record.Set("name", name)
			record.SetVerified(true)
			if err := e.App.Save(record); err != nil {
				log.Printf("Failed to update test user: %v", err)
				return err
			}
			log.Printf("Successfully updated test user %s", email)
		}

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
