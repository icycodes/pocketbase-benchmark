package main

import (
	"log"
	"regexp"
	"strings"
	"unicode"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

var (
	// nonAlphanumericRegex matches any character that is not an ASCII letter or digit.
	nonAlphanumericRegex = regexp.MustCompile(`[^a-z0-9]+`)
	// multiHyphenRegex collapses consecutive hyphens into one.
	multiHyphenRegex = regexp.MustCompile(`-{2,}`)
)

// slugify converts an arbitrary string into a URL-friendly slug.
// Steps:
//  1. Unicode NFD decomposition + strip non-spacing marks (strips accents / diacritics).
//  2. Lowercase.
//  3. Replace non-alphanumeric characters (spaces, punctuation, …) with a hyphen.
//  4. Collapse consecutive hyphens into a single one.
//  5. Trim leading/trailing hyphens.
func slugify(s string) string {
	// Decompose unicode characters and remove non-spacing combining marks (accents).
	t := transform.Chain(norm.NFD, transform.RemoveFunc(func(r rune) bool {
		return unicode.Is(unicode.Mn, r) // Mn = non-spacing mark
	}))
	normalised, _, _ := transform.String(t, s)

	// Lowercase, replace non-alphanumeric chars, collapse/trim hyphens.
	result := strings.ToLower(normalised)
	result = nonAlphanumericRegex.ReplaceAllString(result, "-")
	result = multiHyphenRegex.ReplaceAllString(result, "-")
	result = strings.Trim(result, "-")

	return result
}

func main() {
	app := pocketbase.New()

	// Register a hook that fires before a record is created in the "posts" collection.
	// Validates the title, derives a URL slug, and sets it on the record before save.
	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")

		if title == "" {
			return router.NewBadRequestError("Title cannot be empty", nil)
		}

		e.Record.Set("slug", slugify(title))

		// Continue the hook chain so the record is actually persisted.
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
