package main

import (
	"fmt"
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		users, _ := app.FindAllRecords("users")
		for _, u := range users {
			fmt.Printf("User: %s %s\n", u.Id, u.GetString("email"))
		}
		wallets, _ := app.FindAllRecords("wallets")
		for _, w := range wallets {
			fmt.Printf("Wallet: %s %v\n", w.Id, w.GetFloat("balance"))
		}
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
