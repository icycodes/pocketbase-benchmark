package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnBootstrap().BindFunc(func(se *core.BootstrapEvent) error {
		if err := se.Next(); err != nil {
			return err
		}
		
		collection, err := app.FindCollectionByNameOrId("posts")
		if err != nil {
			collection = core.NewBaseCollection("posts")
			
			collection.Fields.Add(&core.TextField{
				Name: "title",
				Required: true,
			})
			
			collection.Fields.Add(&core.RelationField{
				Name: "owner",
				Required: true,
				CollectionId: "_pb_users_auth_",
				MaxSelect: 1,
			})
		}
		
		viewRule := "owner = @request.auth.id"
		collection.ViewRule = &viewRule
		
		updateRule := "owner = @request.auth.id && @request.body.owner:isset = false"
		collection.UpdateRule = &updateRule
		
		err = app.SaveNoValidate(collection)
		if err != nil {
			return err
		}
		
		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
