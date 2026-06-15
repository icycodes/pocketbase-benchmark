package main

import (
	"log"
	"os"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func ptr(s string) *string { return &s }

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		runID := os.Getenv("ZEALT_RUN_ID")
		if runID == "" {
			runID = "default"
		}
		collectionName := "contacts_" + runID

		// Check if collection exists
		_, err := app.FindCollectionByNameOrId(collectionName)
		if err != nil {
			// Create collection
			collection := core.NewBaseCollection(collectionName)
			collection.ListRule = ptr("")
			collection.ViewRule = ptr("")
			collection.CreateRule = ptr("@request.auth.id != \"\"")
			collection.UpdateRule = ptr("@request.auth.id != \"\"")
			collection.DeleteRule = ptr("@request.auth.id != \"\"")
			
			collection.Fields.Add(&core.TextField{
				Name: "name",
				Required: true,
			})
			collection.Fields.Add(&core.EmailField{
				Name: "email",
				Required: true,
			})

			if err := app.Save(collection); err != nil {
				return err
			}
			log.Println("Created collection:", collectionName)
		}

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
