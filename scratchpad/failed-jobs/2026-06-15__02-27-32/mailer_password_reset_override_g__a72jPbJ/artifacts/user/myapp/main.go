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

	// ----------------------------------------------------------------
	// Bootstrap hook: configure SMTP + seed the test user
	// ----------------------------------------------------------------
	app.OnBootstrap().BindFunc(func(e *core.BootstrapEvent) error {
		if err := e.Next(); err != nil {
			return err
		}

		// Configure SMTP to deliver to local Mailpit instance
		settings := app.Settings()
		settings.SMTP.Enabled = true
		settings.SMTP.Host = "localhost"
		settings.SMTP.Port = 1025
		settings.SMTP.TLS = false
		settings.SMTP.Username = ""
		settings.SMTP.Password = ""
		settings.Meta.SenderName = "Acme"
		settings.Meta.SenderAddress = "no-reply@acme.com"

		if err := app.Save(settings); err != nil {
			// Non-fatal: log and continue (settings may already be fine)
			log.Printf("warning: could not save SMTP settings: %v", err)
		}

		// Seed the test user ----------------------------------------
		email := os.Getenv("TEST_USER_EMAIL")
		if email == "" {
			email = "alice@example.com"
		}
		name := os.Getenv("TEST_USER_NAME")
		if name == "" {
			name = "Alice"
		}

		usersCollection, err := app.FindCollectionByNameOrId("users")
		if err != nil {
			return fmt.Errorf("could not find users collection: %w", err)
		}

		// Only create if the user doesn't exist yet
		existing, _ := app.FindAuthRecordByEmail(usersCollection, email)
		if existing == nil {
			record := core.NewRecord(usersCollection)
			record.Set("email", email)
			record.Set("name", name)
			record.Set("emailVisibility", true)
			record.Set("verified", true)
			// A stable password so the account is usable
			record.SetPassword("Password1234!")
			if err := app.Save(record); err != nil {
				return fmt.Errorf("could not seed user: %w", err)
			}
			log.Printf("seeded user: %s (%s)", name, email)
		} else {
			// Make sure name + verified flag are up to date
			needsSave := false
			if existing.GetString("name") != name {
				existing.Set("name", name)
				needsSave = true
			}
			if !existing.Verified() {
				existing.SetVerified(true)
				needsSave = true
			}
			if needsSave {
				if err := app.Save(existing); err != nil {
					log.Printf("warning: could not update seeded user: %v", err)
				}
			}
		}

		return nil
	})

	// ----------------------------------------------------------------
	// Mailer hook: intercept password-reset emails
	// ----------------------------------------------------------------
	app.OnMailerRecordPasswordResetSend("users").BindFunc(func(e *core.MailerRecordEvent) error {
		// Determine display name: use name field, fall back to email
		displayName := e.Record.GetString("name")
		if displayName == "" {
			displayName = e.Record.Email()
		}

		// Extract the token that PocketBase already generated
		token, _ := e.Meta["token"].(string)

		resetLink := "https://acme.com/reset?token=" + token

		// Override subject and HTML body
		e.Message.Subject = "Reset your acme.com password"
		e.Message.HTML = fmt.Sprintf("Hi %s! Use this link: %s", displayName, resetLink)

		// Call e.Next() so the mailer still delivers via SMTP
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
