package main

import (
	"encoding/json"
	"log"
	"strings"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func ptr(s string) *string {
	return &s
}

func main() {
	app := pocketbase.New()

	// Automatically verify, create, or update collections on Serve
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// Verify, create, or update posts collection
		posts, err := e.App.FindCollectionByNameOrId("posts")
		if err != nil {
			posts = core.NewBaseCollection("posts")
			posts.Fields.Add(&core.TextField{
				Name:     "title",
				Required: true,
			})
		}
		posts.ListRule = ptr("")
		posts.ViewRule = ptr("")
		posts.CreateRule = ptr("")
		posts.UpdateRule = ptr("")
		posts.DeleteRule = ptr("")
		if err := e.App.Save(posts); err != nil {
			log.Printf("Error saving posts collection: %v", err)
			return err
		}
		log.Println("Successfully verified/updated posts collection")

		// Verify, create, or update audit_log collection
		auditLog, err := e.App.FindCollectionByNameOrId("audit_log")
		if err != nil {
			auditLog = core.NewBaseCollection("audit_log")
			auditLog.Fields.Add(
				&core.TextField{Name: "actor"},
				&core.TextField{Name: "action"},
				&core.TextField{Name: "collection"},
				&core.TextField{Name: "record"},
				&core.DateField{Name: "at"},
				&core.JSONField{Name: "diff"},
			)
		}
		auditLog.ListRule = ptr("")
		auditLog.ViewRule = ptr("")
		if err := e.App.Save(auditLog); err != nil {
			log.Printf("Error saving audit_log collection: %v", err)
			return err
		}
		log.Println("Successfully verified/updated audit_log collection")

		// Seed a regular user if not exists
		userCollection, err := e.App.FindCollectionByNameOrId("users")
		if err == nil {
			existing, _ := e.App.FindFirstRecordByData("users", "email", "test@example.com")
			if existing == nil {
				user := core.NewRecord(userCollection)
				user.Set("email", "test@example.com")
				user.SetPassword("1234567890")
				user.Set("emailVisibility", true)
				user.Set("verified", true)
				if err := e.App.Save(user); err != nil {
					log.Printf("Error creating seed user: %v", err)
				} else {
					log.Println("Successfully created seed user test@example.com")
				}
			}
		}

		return e.Next()
	})

	// Global hook for record create requests
	app.OnRecordCreateRequest().BindFunc(func(e *core.RecordRequestEvent) error {
		collectionName := e.Record.Collection().Name
		// Ignore system collections and audit_log itself
		if collectionName == "audit_log" || strings.HasPrefix(collectionName, "_") {
			return e.Next()
		}

		// Execute the actual creation
		if err := e.Next(); err != nil {
			return err
		}

		// Determine actor
		actor := "anon"
		if e.Auth != nil {
			actor = e.Auth.Id
		}

		// Create audit log row
		auditLogCollection, err := e.App.FindCollectionByNameOrId("audit_log")
		if err != nil {
			return err
		}

		logRecord := core.NewRecord(auditLogCollection)
		logRecord.Set("actor", actor)
		logRecord.Set("action", "create")
		logRecord.Set("collection", collectionName)
		logRecord.Set("record", e.Record.Id)
		logRecord.Set("at", time.Now())
		logRecord.Set("diff", map[string]any{})

		if err := e.App.Save(logRecord); err != nil {
			log.Printf("Error saving audit log for create: %v", err)
			return err
		}

		return nil
	})

	// Global hook for record update requests
	app.OnRecordUpdateRequest().BindFunc(func(e *core.RecordRequestEvent) error {
		collectionName := e.Record.Collection().Name
		// Ignore system collections and audit_log itself
		if collectionName == "audit_log" || strings.HasPrefix(collectionName, "_") {
			return e.Next()
		}

		// Capture original record and calculate diff BEFORE saving
		oldRecord := e.Record.Original()
		diffMap := map[string]any{}
		for _, name := range e.Record.Collection().Fields.FieldNames() {
			if name == "id" || name == "created" || name == "updated" {
				continue
			}
			oldVal := oldRecord.Get(name)
			newVal := e.Record.Get(name)

			// Compare JSON representations
			oldBytes, _ := json.Marshal(oldVal)
			newBytes, _ := json.Marshal(newVal)
			if string(oldBytes) != string(newBytes) {
				diffMap[name] = map[string]any{
					"old": oldVal,
					"new": newVal,
				}
			}
		}

		// Execute the actual update
		if err := e.Next(); err != nil {
			return err
		}

		// Determine actor
		actor := "anon"
		if e.Auth != nil {
			actor = e.Auth.Id
		}

		// Create audit log row
		auditLogCollection, err := e.App.FindCollectionByNameOrId("audit_log")
		if err != nil {
			return err
		}

		logRecord := core.NewRecord(auditLogCollection)
		logRecord.Set("actor", actor)
		logRecord.Set("action", "update")
		logRecord.Set("collection", collectionName)
		logRecord.Set("record", e.Record.Id)
		logRecord.Set("at", time.Now())
		logRecord.Set("diff", diffMap)

		if err := e.App.Save(logRecord); err != nil {
			log.Printf("Error saving audit log for update: %v", err)
			return err
		}

		return nil
	})

	// Global hook for record delete requests
	app.OnRecordDeleteRequest().BindFunc(func(e *core.RecordRequestEvent) error {
		collectionName := e.Record.Collection().Name
		// Ignore system collections and audit_log itself
		if collectionName == "audit_log" || strings.HasPrefix(collectionName, "_") {
			return e.Next()
		}

		// Execute the actual deletion
		if err := e.Next(); err != nil {
			return err
		}

		// Determine actor
		actor := "anon"
		if e.Auth != nil {
			actor = e.Auth.Id
		}

		// Create audit log row
		auditLogCollection, err := e.App.FindCollectionByNameOrId("audit_log")
		if err != nil {
			return err
		}

		logRecord := core.NewRecord(auditLogCollection)
		logRecord.Set("actor", actor)
		logRecord.Set("action", "delete")
		logRecord.Set("collection", collectionName)
		logRecord.Set("record", e.Record.Id)
		logRecord.Set("at", time.Now())
		logRecord.Set("diff", map[string]any{})

		if err := e.App.Save(logRecord); err != nil {
			log.Printf("Error saving audit log for delete: %v", err)
			return err
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
