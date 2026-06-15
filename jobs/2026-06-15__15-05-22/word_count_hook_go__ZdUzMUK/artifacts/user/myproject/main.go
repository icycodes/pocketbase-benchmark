package main

import (
	"log"

	"github.com/pocketbase/pocketbase"

	_ "pbapp/migrations"
)

func main() {
	app := pocketbase.New()

	// TODO: Register PocketBase event hooks on the "articles" collection so that
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

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
