package main

import (
	"log"
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

func Slugify(s string) string {
	s = strings.ToLower(s)
	s = regexp.MustCompile(`[^a-z0-9]+`).ReplaceAllString(s, "-")
	return strings.Trim(s, "-")
}

func main() {
	app := pocketbase.New()

	app.OnBootstrap().BindFunc(func(e *core.BootstrapEvent) error {
		if err := e.Next(); err != nil {
			return err
		}

		collection, err := app.FindCollectionByNameOrId("posts")
		if err != nil {
			collection = core.NewCollection(&core.Collection{
				Name: "posts",
				Type: core.CollectionTypeBase,
			})

			collection.Fields.Add(&core.TextField{
				Name: "title",
			})
			collection.Fields.Add(&core.TextField{
				Name: "slug",
			})

			if err := app.Save(collection); err != nil {
				return err
			}
		}

		return nil
	})

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return apis.NewBadRequestError("Title cannot be empty", nil)
		}

		slug := Slugify(title)
		e.Record.Set("slug", slug)

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
