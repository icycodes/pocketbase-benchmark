package migrations

import (
	"os"

	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	runId := os.Getenv("ZEALT_RUN_ID")
	collectionName := "contacts_" + runId

	migrations.Register(
		// Up migration: create the collection
		func(txApp core.App) error {
			col := core.NewBaseCollection(collectionName)

			// Public read access
			col.ListRule = types.Pointer("")
			col.ViewRule = types.Pointer("")

			// Only authenticated users can create/update/delete
			col.CreateRule = types.Pointer("@request.auth.id != \"\"")
			col.UpdateRule = types.Pointer("@request.auth.id != \"\"")
			col.DeleteRule = types.Pointer("@request.auth.id != \"\"")

			// Add schema fields
			col.Fields.Add(&core.TextField{
				Name:     "name",
				Required: true,
			})

			col.Fields.Add(&core.EmailField{
				Name:     "email",
				Required: true,
			})

			return txApp.Save(col)
		},
		// Down migration: delete the collection
		func(txApp core.App) error {
			col, err := txApp.FindCachedCollectionByNameOrId(collectionName)
			if err != nil {
				return err
			}
			return txApp.Delete(col)
		},
	)
}
