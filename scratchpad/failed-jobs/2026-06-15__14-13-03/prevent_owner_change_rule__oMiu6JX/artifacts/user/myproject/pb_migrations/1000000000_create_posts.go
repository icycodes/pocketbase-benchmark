package pb_migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(app core.App) error {
		// Retrieve the built-in users collection to get its ID for the relation.
		usersCollection, err := app.FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		// Build the posts collection.
		posts := core.NewCollection(core.CollectionTypeBase, "posts")

		// --- Fields ---
		posts.Fields.Add(&core.TextField{
			Name:     "title",
			Required: true,
		})

		posts.Fields.Add(&core.RelationField{
			Name:         "owner",
			CollectionId: usersCollection.Id,
			// Single relation (not multi).
			MaxSelect: 1,
			Required:  true,
		})

		// --- API Rules ---

		// List / View: only the owner can list or view their own posts.
		ownerRule := types.Pointer("owner = @request.auth.id")
		posts.ListRule = ownerRule
		posts.ViewRule = ownerRule

		// Create: authenticated users can create; ownership is enforced by
		// requiring the owner field to equal the authenticated user.
		posts.CreateRule = types.Pointer("@request.auth.id != '' && @request.body.owner = @request.auth.id")

		// Update rule enforces two conditions (both must be true):
		//   1. The record's current owner must be the authenticated user.
		//   2. The request body must NOT include an "owner" field
		//      (`:isset` returns true when the field is present in the payload).
		posts.UpdateRule = types.Pointer(
			"owner = @request.auth.id && @request.body.owner:isset = false",
		)

		// Delete: only the owner can delete their post.
		posts.DeleteRule = types.Pointer("owner = @request.auth.id")

		return app.Save(posts)
	}, func(app core.App) error {
		// Down migration: remove the posts collection.
		collection, err := app.FindCollectionByNameOrId("posts")
		if err != nil {
			return err
		}
		return app.Delete(collection)
	})
}
