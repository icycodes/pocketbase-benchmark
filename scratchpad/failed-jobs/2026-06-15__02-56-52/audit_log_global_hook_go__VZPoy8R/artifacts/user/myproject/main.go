package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnRecordCreate().BindFunc(func(e *core.RecordEvent) error {
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
