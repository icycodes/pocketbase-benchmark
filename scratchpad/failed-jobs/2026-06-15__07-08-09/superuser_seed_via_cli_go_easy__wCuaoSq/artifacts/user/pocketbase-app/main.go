package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/spf13/cobra"
)

func main() {
	app := pocketbase.New()

	app.RootCmd.AddCommand(&cobra.Command{
		Use:   "seed-superuser <email> <password>",
		Short: "Seeds a superuser with the given email and password",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			email := args[0]
			password := args[1]

			// Get the superusers collection
			collection, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
			if err != nil {
				return err
			}

			// Try to find an existing superuser by email
			record, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)
			if err != nil {
				// If not found, create a new record
				record = core.NewRecord(collection)
				record.SetEmail(email)
			}

			// Set/update the password
			record.SetPassword(password)

			// Save the record
			if err := app.Save(record); err != nil {
				return err
			}

			cmd.Printf("Successfully seeded superuser %s\n", email)
			return nil
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
