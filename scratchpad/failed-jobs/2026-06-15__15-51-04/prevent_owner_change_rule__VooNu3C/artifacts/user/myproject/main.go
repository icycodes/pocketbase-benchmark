package main

import (
	"log"

	"github.com/pocketbase/pocketbase"

	// Register custom app migrations
	_ "myproject/pb_migrations"
)

func main() {
	app := pocketbase.New()

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
