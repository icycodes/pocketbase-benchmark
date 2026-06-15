package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	pbcore "github.com/pocketbase/pocketbase/core"
	"myproject/core"
)

func main() {
	app := pocketbase.New()

	// Automatically create the "posts" collection on startup if it doesn't exist
	app.OnServe().BindFunc(func(e *pbcore.ServeEvent) error {
		_, err := app.FindCollectionByNameOrId("posts")
		if err != nil {
			log.Println("Posts collection not found. Creating it programmatically...")
			collection := pbcore.NewCollection(pbcore.CollectionTypeBase, "posts")

			// Define fields
			collection.Fields.Add(&pbcore.TextField{
				Name: "title",
			})
			collection.Fields.Add(&pbcore.TextField{
				Name: "slug",
			})

			// Make the posts collection completely public for testing
			publicRule := ""
			collection.ListRule = &publicRule
			collection.ViewRule = &publicRule
			collection.CreateRule = &publicRule
			collection.UpdateRule = &publicRule
			collection.DeleteRule = &publicRule

			if err := app.Save(collection); err != nil {
				log.Printf("Failed to create posts collection: %v", err)
				return err
			}
			log.Println("Successfully created posts collection")
		}
		return e.Next()
	})

	// Register the record create request hook for the "posts" collection
	app.OnRecordCreateRequest("posts").BindFunc(func(e *pbcore.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return e.BadRequestError("Title cannot be empty", nil)
		}

		// Generate slug from title
		e.Record.Set("slug", core.Slugify(title))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
