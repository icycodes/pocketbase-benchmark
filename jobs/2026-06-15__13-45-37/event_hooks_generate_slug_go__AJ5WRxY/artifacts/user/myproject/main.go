package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	pbcore "github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
	"myproject/core"
)

type customApp struct {
	*pocketbase.PocketBase
}

func (app *customApp) OnRecordBeforeCreateRequest(tags ...string) *hook.TaggedHook[*pbcore.RecordRequestEvent] {
	return app.OnRecordCreateRequest(tags...)
}

func ptr[T any](v T) *T {
	return &v
}

func main() {
	pb := pocketbase.New()
	app := &customApp{pb}

	app.OnRecordBeforeCreateRequest("posts").BindFunc(func(e *pbcore.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return apis.NewBadRequestError("Title cannot be empty", nil)
		}

		slug := core.Slugify(title)
		e.Record.Set("slug", slug)

		return e.Next()
	})

	app.OnServe().BindFunc(func(e *pbcore.ServeEvent) error {
		// check if "posts" collection exists, if not, create it
		_, err := e.App.FindCollectionByNameOrId("posts")
		if err != nil {
			collection := pbcore.NewCollection(pbcore.CollectionTypeBase, "posts")
			collection.ListRule = ptr("")
			collection.ViewRule = ptr("")
			collection.CreateRule = ptr("")
			collection.UpdateRule = ptr("")
			collection.DeleteRule = ptr("")

			collection.Fields.Add(&pbcore.TextField{
				Name: "title",
			})
			collection.Fields.Add(&pbcore.TextField{
				Name: "slug",
			})

			if err := e.App.Save(collection); err != nil {
				return err
			}
		}
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
