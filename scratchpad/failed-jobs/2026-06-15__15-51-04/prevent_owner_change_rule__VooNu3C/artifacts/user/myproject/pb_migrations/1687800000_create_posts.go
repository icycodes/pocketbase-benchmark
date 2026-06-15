package pb_migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	core.AppMigrations.Register(
		func(txApp core.App) error {
			// Create the "posts" collection
			posts := core.NewBaseCollection("posts")

			// Add the "title" text field
			posts.Fields.Add(&core.TextField{
				Name:     "title",
				Required: true,
			})

			// Add the "owner" relation field targeting the built-in "users" collection
			posts.Fields.Add(&core.RelationField{
				Name:         "owner",
				Required:     true,
				CollectionId: "_pb_users_auth_",
				MaxSelect:    1,
			})

			// Set API rules
			// List/View: only authenticated users can list/view all posts
			posts.ListRule = types.Pointer("@request.auth.id != \"\"")
			posts.ViewRule = types.Pointer("@request.auth.id != \"\"")

			// Create: the owner must be the current authenticated user
			posts.CreateRule = types.Pointer("@request.auth.id != \"\" && @request.body.owner = @request.auth.id")

			// Update: only the owner can update, and the owner field cannot be changed
			posts.UpdateRule = types.Pointer("owner = @request.auth.id && @request.body.owner:isset = false")

			// Delete: only the owner can delete
			posts.DeleteRule = types.Pointer("owner = @request.auth.id")

			return txApp.Save(posts)
		},
		func(txApp core.App) error {
			collection, err := txApp.FindCachedCollectionByNameOrId("posts")
			if err != nil {
				return err
			}

			return txApp.Delete(collection)
		},
	)
}
