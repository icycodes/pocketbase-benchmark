package main

import (
	"fmt"
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/spf13/cobra"
)

func main() {
	app := pocketbase.New()

	app.RootCmd.AddCommand(&cobra.Command{
		Use:   "seed-superuser <email> <password>",
		Short: "Seed a superuser account (upsert)",
		Args:  cobra.ExactArgs(2),
		Run: func(cmd *cobra.Command, args []string) {
			email := args[0]
			password := args[1]

			collection, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
			if err != nil {
				log.Fatalf("Failed to find superusers collection: %v", err)
			}

			record, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)
			if err != nil {
				// No existing record found, create a new one
				record = core.NewRecord(collection)
			}

			record.Set("email", email)
			record.Set("password", password)

			if err := app.Save(record); err != nil {
				log.Fatalf("Failed to save superuser: %v", err)
			}

			fmt.Printf("Superuser %s saved successfully.\n", email)
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}