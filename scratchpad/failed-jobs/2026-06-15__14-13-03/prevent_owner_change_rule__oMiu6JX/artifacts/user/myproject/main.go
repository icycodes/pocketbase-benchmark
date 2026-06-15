package main

import (
	"log"
	"os"

	_ "myproject/pb_migrations"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"
)

func main() {
	app := pocketbase.New()

	// Register the migrate command so pb_migrations run automatically on serve.
	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		// Auto-run pending migrations when the app starts.
		Automigrate: true,
	})

	if err := app.Start(); err != nil {
		log.Println(err)
		os.Exit(1)
	}
}
