package main

import (
	"fmt"
	"log"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		cols, err := e.App.FindAllCollections()
		if err != nil { return err }
		for _, c := range cols {
			fmt.Println(c.Name)
		}
		return nil
	})
	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
