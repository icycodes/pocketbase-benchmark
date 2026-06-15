package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"myproject/core"
)

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return e.BadRequestError("Title cannot be empty", nil)
		}

		e.Record.Set("slug", core.Slugify(title))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
