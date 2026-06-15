package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	// Register the local migrations package (creates the "articles" collection).
	_ "articles-app/migrations"
)

func main() {
	app := pocketbase.New()

	// Apply pending migrations automatically on `serve`.
	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	// TODO: register the OnRecordCreateRequest("articles") hook here so that
	// every successful article creation request receives an auto-generated slug
	// and every empty/whitespace-only title is rejected with a 400 response.

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
