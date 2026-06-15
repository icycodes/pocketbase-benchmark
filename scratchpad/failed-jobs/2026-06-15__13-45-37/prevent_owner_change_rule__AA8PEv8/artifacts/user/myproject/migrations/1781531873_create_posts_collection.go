package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(app core.App) error {
		// Create the posts collection
		collection := core.NewBaseCollection("posts")

		// Set rules
		collection.ListRule = types.Pointer("")
		collection.ViewRule = types.Pointer("")
		collection.CreateRule = types.Pointer("@request.auth.id != ''")
		collection.UpdateRule = types.Pointer("owner = @request.auth.id && @request.body.owner:isset = false")
		collection.DeleteRule = types.Pointer("owner = @request.auth.id")

		// Add fields
		collection.Fields.Add(&core.TextField{
			Name:     "title",
			Required: true,
		})

		// Find users collection to link relation
		usersCollection, err := app.FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		collection.Fields.Add(&core.RelationField{
			Name:         "owner",
			Required:     true,
			CollectionId: usersCollection.Id,
			MaxSelect:    1,
		})

		// Add autodate fields
		collection.Fields.Add(&core.AutodateField{
			Name:     "created",
			OnCreate: true,
		})
		collection.Fields.Add(&core.AutodateField{
			Name:     "updated",
			OnCreate: true,
			OnUpdate: true,
		})

		return app.Save(collection)
	}, func(app core.App) error {
		collection, err := app.FindCollectionByNameOrId("posts")
		if err == nil {
			return app.Delete(collection)
		}
		return nil
	})
}
