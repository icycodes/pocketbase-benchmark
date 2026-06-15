package main

import (
	"strings"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			err := app.RunInTransaction(func(txApp core.App) error {
				_, err := txApp.FindRecordById("wallets", "123")
				return err
			})
			if err != nil && strings.Contains(err.Error(), "database is locked") {
				// retry
			}
			return e.JSON(200, map[string]any{"ok": true})
		})
		return se.Next()
	})
}
