package main

import (
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func slugify(title string) string {
	return strings.ReplaceAll(strings.ToLower(title), " ", "-")
}

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return e.BadRequestError("Title cannot be empty", nil)
		}

		// The prompt requested core.Slugify(title), but as of v0.31.0 it does not exist.
		// Using a custom slugify function to generate the slug.
		// core.Slugify(title)
		e.Record.Set("slug", slugify(title))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
