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
		Short: "Create or update a superuser account",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			email := args[0]
			password := args[1]

			// Bootstrap the app so the database is available.
			if err := app.Bootstrap(); err != nil {
				return err
			}

			// Try to find an existing superuser with the given email (upsert).
			record, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)
			if err != nil {
				// Record not found – create a new one.
				collection, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
				if err != nil {
					return err
				}
				record = core.NewRecord(collection)
				record.Set("email", email)
			}

			record.SetPassword(password)

			if err := app.Save(record); err != nil {
				return err
			}

			cmd.Printf("Superuser %q saved successfully.\n", email)
			return nil
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
