package main

import (
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func slugify(input string) string {
	// Convert to lowercase
	s := strings.ToLower(input)

	// Replace non-alphanumeric characters (except hyphens) with hyphens
	re := regexp.MustCompile(`[^a-z0-9]+`)
	s = re.ReplaceAllString(s, "-")

	// Remove leading and trailing hyphens
	s = strings.Trim(s, "-")

	// Collapse multiple consecutive hyphens into a single one
	re = regexp.MustCompile(`-+`)
	s = re.ReplaceAllString(s, "-")

	return s
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
		panic(err)
	}
}
