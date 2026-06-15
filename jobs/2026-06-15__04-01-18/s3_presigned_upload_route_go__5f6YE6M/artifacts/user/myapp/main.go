package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	// Bootstrap collections and seed data on startup
	app.OnBeforeServe().Add(func(e *core.ServeEvent) error {
		if err := bootstrapCollections(app); err != nil {
			log.Printf("ERROR: failed to bootstrap collections: %v", err)
			return err
		}
		if err := seedData(app); err != nil {
			log.Printf("ERROR: failed to seed data: %v", err)
			return err
		}
		return nil
	})

	// Register the uploads routes
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		registerRoutes(app, se)
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
