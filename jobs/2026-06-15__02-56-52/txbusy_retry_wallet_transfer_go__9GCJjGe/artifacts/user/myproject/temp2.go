package main

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			return e.JSON(200, map[string]any{"ok": true})
		})
		return se.Next()
	})
}
