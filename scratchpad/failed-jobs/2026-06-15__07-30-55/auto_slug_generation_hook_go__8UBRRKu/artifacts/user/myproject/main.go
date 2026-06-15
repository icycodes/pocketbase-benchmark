package main

import (
	"log"
	"net/http"
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

var nonAlphanumericRegex = regexp.MustCompile(`[^a-z0-9]+`)

// slugify converts a title string into a URL-friendly slug.
// e.g. "Hello World!" -> "hello-world"
func slugify(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = nonAlphanumericRegex.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	return s
}

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return apis.NewApiError(http.StatusBadRequest, "title is required", nil)
		}

		slug := slugify(title)
		e.Record.Set("slug", slug)

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
