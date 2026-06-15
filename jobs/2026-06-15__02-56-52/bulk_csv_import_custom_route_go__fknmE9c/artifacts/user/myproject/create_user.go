package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		users, _ := se.App.FindCollectionByNameOrId("users")
		record := core.NewRecord(users)
		record.Set("email", "user@example.com")
		record.Set("password", "password123")
		record.Set("passwordConfirm", "password123")
		record.Set("verified", true)
		if err := se.App.Save(record); err != nil {
			log.Fatal(err)
		}
		return se.Next()
	})
	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
