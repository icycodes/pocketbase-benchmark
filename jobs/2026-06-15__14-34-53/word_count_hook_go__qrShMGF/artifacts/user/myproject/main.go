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

	hook := func(e *core.RecordRequestEvent) error {
		content := e.Record.GetString("content")
		wordCount := len(strings.Fields(content))
		
		var readingTime int
		if wordCount > 0 {
			readingTime = int(math.Ceil(float64(wordCount) / 200.0))
		} else {
			readingTime = 0
		}

		e.Record.Set("word_count", wordCount)
		e.Record.Set("reading_time_minutes", readingTime)

		return e.Next()
	}

	app.OnRecordCreateRequest("articles").BindFunc(hook)
	app.OnRecordUpdateRequest("articles").BindFunc(hook)

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
