package main

import (
	"log"
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

var (
	nonAlphanumericRegex = regexp.MustCompile(`[^a-z0-9]+`)
	leadingTrailingDash  = regexp.MustCompile(`^-|-$`)
)

// slugify converts a title string into a URL-friendly slug.
func slugify(title string) string {
	slug := strings.ToLower(title)
	slug = nonAlphanumericRegex.ReplaceAllString(slug, "-")
	slug = leadingTrailingDash.ReplaceAllString(slug, "")
	return slug
}

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")

		if title == "" {
			return e.BadRequestError("Title cannot be empty", nil)
		}

		e.Record.Set("slug", slugify(title))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
