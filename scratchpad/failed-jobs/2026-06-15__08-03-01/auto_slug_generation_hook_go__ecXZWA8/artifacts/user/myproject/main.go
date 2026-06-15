package main

import (
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

func slugify(s string) string {
	s = strings.ToLower(s)
	// Replace spaces with hyphens
	s = strings.ReplaceAll(s, " ", "-")
	// Remove all characters except lowercase letters, numbers, and hyphens
	re := regexp.MustCompile("[^a-z0-9-]")
	s = re.ReplaceAllString(s, "")
	// Replace consecutive hyphens with a single hyphen
	re2 := regexp.MustCompile("-+")
	s = re2.ReplaceAllString(s, "-")
	// Trim leading and trailing hyphens
	s = strings.Trim(s, "-")
	return s
}

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")

		if title == "" {
			return apis.NewBadRequestError("title is required", nil)
		}

		slug := slugify(title)
		e.Record.Set("slug", slug)

		return e.Next()
	})

	if err := app.Start(); err != nil {
		panic(err)
	}
}