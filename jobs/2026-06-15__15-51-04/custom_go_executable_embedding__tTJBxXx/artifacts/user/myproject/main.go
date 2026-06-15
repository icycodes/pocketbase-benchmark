package main

import (
	"log"
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

// slugify converts a string into a URL-friendly slug.
func slugify(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))

	// Replace non-alphanumeric characters (except hyphens) with hyphens
	re := regexp.MustCompile(`[^a-z0-9]+`)
	s = re.ReplaceAllString(s, "-")

	// Remove leading and trailing hyphens
	s = strings.Trim(s, "-")

	return s
}

func main() {
	app := pocketbase.New()

	// Register a hook for the "posts" collection that intercepts record creation
	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")

		// If title is empty or missing, return a 400 Bad Request error
		if title == "" {
			return e.BadRequestError("Title cannot be empty", nil)
		}

		// Generate a slug from the title
		slug := slugify(title)
		e.Record.Set("slug", slug)

		// Continue to the next handler in the chain (the default form submission)
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
