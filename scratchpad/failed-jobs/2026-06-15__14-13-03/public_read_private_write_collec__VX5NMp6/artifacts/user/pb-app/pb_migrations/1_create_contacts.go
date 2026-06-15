package migrations

import (
	"os"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		runID := os.Getenv("ZEALT_RUN_ID")
		collectionName := "contacts_" + runID

		// Check if collection already exists
		existing, _ := app.FindCollectionByNameOrId(collectionName)
		if existing != nil {
			return nil
		}

		collection := core.NewBaseCollection(collectionName)

		// Schema fields
		nameField := &core.TextField{
			Name:     "name",
			Required: true,
		}
		emailField := &core.EmailField{
			Name:     "email",
			Required: true,
		}

		collection.Fields.Add(nameField, emailField)

		// API rules:
		// - List/View: public (empty string = anyone)
		// - Create/Update/Delete: authenticated users only
		listRule := ""
		viewRule := ""
		createRule := "@request.auth.id != \"\""
		updateRule := "@request.auth.id != \"\""
		deleteRule := "@request.auth.id != \"\""

		collection.ListRule = &listRule
		collection.ViewRule = &viewRule
		collection.CreateRule = &createRule
		collection.UpdateRule = &updateRule
		collection.DeleteRule = &deleteRule

		return app.Save(collection)
	}, func(app core.App) error {
		// Rollback: delete the collection
		runID := os.Getenv("ZEALT_RUN_ID")
		collectionName := "contacts_" + runID

		collection, err := app.FindCollectionByNameOrId(collectionName)
		if err != nil {
			return nil // already gone
		}
		return app.Delete(collection)
	})
}
