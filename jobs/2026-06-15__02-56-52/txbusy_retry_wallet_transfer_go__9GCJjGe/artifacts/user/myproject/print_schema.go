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
		cols, _ := app.FindAllCollections()
		for _, c := range cols {
			fmt.Printf("Collection: %s\n", c.Name)
			for _, f := range c.Fields {
				fmt.Printf("  Field: %s (%s)\n", f.GetName(), f.Type())
			}
		}
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
