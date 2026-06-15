package main

import (
	"log"
	"math"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"

	_ "pbapp/migrations"
)

// computeWordStats derives word_count and reading_time_minutes from a content string.
// reading_time_minutes = ceil(word_count / 200), with 0 words yielding 0 minutes.
func computeWordStats(content string) (wordCount int, readingTime int) {
	words := strings.Fields(content)
	wordCount = len(words)
	if wordCount == 0 {
		readingTime = 0
	} else {
		readingTime = int(math.Ceil(float64(wordCount) / 200.0))
	}
	return
}

func main() {
	app := pocketbase.New()

	// Hook: articles record CREATE via REST API
	app.OnRecordCreateRequest("articles").BindFunc(func(e *core.RecordRequestEvent) error {
		content := e.Record.GetString("content")
		wordCount, readingTime := computeWordStats(content)
		e.Record.Set("word_count", wordCount)
		e.Record.Set("reading_time_minutes", readingTime)
		return e.Next()
	})

	// Hook: articles record UPDATE via REST API
	app.OnRecordUpdateRequest("articles").BindFunc(func(e *core.RecordRequestEvent) error {
		content := e.Record.GetString("content")
		wordCount, readingTime := computeWordStats(content)
		e.Record.Set("word_count", wordCount)
		e.Record.Set("reading_time_minutes", readingTime)
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
