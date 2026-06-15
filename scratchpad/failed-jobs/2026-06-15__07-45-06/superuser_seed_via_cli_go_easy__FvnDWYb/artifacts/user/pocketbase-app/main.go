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
		Use:   "seed-superuser [email] [password]",
		Short: "Seed a superuser",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			email := args[0]
			password := args[1]

			collection, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
			if err != nil {
				return err
			}

			record, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)
			if err != nil {
				// Record not found, create a new one
				record = core.NewRecord(collection)
				record.SetEmail(email)
			}

			record.SetPassword(password)
			return app.Save(record)
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
