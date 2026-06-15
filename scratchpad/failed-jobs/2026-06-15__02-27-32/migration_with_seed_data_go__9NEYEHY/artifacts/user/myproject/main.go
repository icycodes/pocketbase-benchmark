package main

import (
	"log"
	"os"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	// blank import to trigger the migration init()
	_ "myproject/migrations"
)

func main() {
	app := pocketbase.New()

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		// automigrate is only useful during development; keep it off for a
		// deterministic production binary
		Automigrate: false,
	})

	if err := app.Start(); err != nil {
		log.Println(err)
		os.Exit(1)
	}
}
