package main

import (
	"database/sql"
	"errors"
	"fmt"
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/spf13/cobra"
)

func main() {
	app := pocketbase.New()

	app.RootCmd.AddCommand(seedSuperuserCommand(app))

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func seedSuperuserCommand(app core.App) *cobra.Command {
	return &cobra.Command{
		Use:   "seed-superuser <email> <password>",
		Short: "Seed a superuser (create or update password)",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			email := args[0]
			password := args[1]

			// Try to find an existing superuser by email
			existingRecord, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)
			if err != nil && !errors.Is(err, sql.ErrNoRows) {
				return fmt.Errorf("failed to lookup superuser: %w", err)
			}

			if existingRecord != nil {
				// Upsert: update the existing superuser's password
				existingRecord.SetPassword(password)
				if err := app.Save(existingRecord); err != nil {
					return fmt.Errorf("failed to update superuser: %w", err)
				}
				fmt.Printf("Superuser %q already existed — password updated.\n", email)
				return nil
			}

			// Create a new superuser
			collection, err := app.FindCachedCollectionByNameOrId(core.CollectionNameSuperusers)
			if err != nil {
				return fmt.Errorf("failed to fetch superusers collection: %w", err)
			}

			record := core.NewRecord(collection)
			record.SetEmail(email)
			record.SetPassword(password)

			if err := app.Save(record); err != nil {
				return fmt.Errorf("failed to create superuser: %w", err)
			}

			fmt.Printf("Superuser %q created successfully.\n", email)
			return nil
		},
	}
}
