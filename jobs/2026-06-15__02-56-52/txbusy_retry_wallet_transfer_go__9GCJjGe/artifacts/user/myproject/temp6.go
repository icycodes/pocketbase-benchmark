package main

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/dbx"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			return app.RunInTransaction(func(txApp core.App) error {
				_, err := txApp.DB().NewQuery("UPDATE wallets SET id=id WHERE id={:id}").Bind(dbx.Params{"id": "123"}).Execute()
				return err
			})
		})
		return se.Next()
	})
}
