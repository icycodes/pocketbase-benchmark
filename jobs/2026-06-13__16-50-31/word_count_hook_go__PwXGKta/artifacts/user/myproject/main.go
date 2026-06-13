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

	// Register PocketBase event hooks on the "articles" collection so that
	// on every record create and record update REST request the server
	// automatically computes the following fields and writes them onto the
	// record before it is saved:
	//
	//   - word_count            (int): number of whitespace-separated words
	//                                  in the submitted "content" field.
	//   - reading_time_minutes  (int): ceil(word_count / 200), where 0 words
	//                                  must yield 0 minutes.
	//
	// The computed values must overwrite any values supplied by the client
	// for word_count / reading_time_minutes. Don't forget to return e.Next()
	// from each hook handler so the chain continues and the record is saved.

	app.OnRecordCreateRequest("articles").BindFunc(func(e *core.RecordRequestEvent) error {
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
	})

	app.OnRecordUpdateRequest("articles").BindFunc(func(e *core.RecordRequestEvent) error {
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
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
