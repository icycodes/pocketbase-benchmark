package main

import (
	"log"
	"math"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"

	_ "pbapp/migrations"
)

func main() {
	app := pocketbase.New()

	// Shared hook handler that computes word_count and reading_time_minutes
	// from the submitted "content" field.
	computeReadingStats := func(e *core.RecordRequestEvent) error {
		content := e.Record.GetString("content")
		words := strings.Fields(content)
		wordCount := len(words)

		readingTime := 0
		if wordCount > 0 {
			readingTime = int(math.Ceil(float64(wordCount) / 200.0))
		}

		e.Record.Set("word_count", wordCount)
		e.Record.Set("reading_time_minutes", readingTime)

		return e.Next()
	}

	app.OnRecordCreateRequest("articles").BindFunc(computeReadingStats)
	app.OnRecordUpdateRequest("articles").BindFunc(computeReadingStats)

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
