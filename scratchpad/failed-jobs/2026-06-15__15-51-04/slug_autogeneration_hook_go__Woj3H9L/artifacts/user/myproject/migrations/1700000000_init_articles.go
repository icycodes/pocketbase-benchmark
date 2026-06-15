package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(app core.App) error {
		collection := core.NewBaseCollection("articles")

		// Open rules so the verifier can exercise the public REST API without auth.
		collection.ListRule = types.Pointer("")
		collection.ViewRule = types.Pointer("")
		collection.CreateRule = types.Pointer("")
		collection.UpdateRule = types.Pointer("")
		collection.DeleteRule = types.Pointer("")

		collection.Fields.Add(
			&core.TextField{Name: "title", Required: true},
			&core.TextField{Name: "slug"},
			&core.TextField{Name: "content"},
		)

		return app.Save(collection)
	}, func(app core.App) error {
		collection, err := app.FindCollectionByNameOrId("articles")
		if err != nil {
			return err
		}
		return app.Delete(collection)
	})
}
