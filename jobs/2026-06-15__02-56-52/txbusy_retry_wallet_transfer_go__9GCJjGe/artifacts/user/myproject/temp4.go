package main

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			type TransferReq struct {
				FromId string  `json:"fromId"`
				ToId   string  `json:"toId"`
				Amount float64 `json:"amount"`
			}
			req := new(TransferReq)
			if err := e.BindBody(req); err != nil {
				return e.JSON(400, map[string]any{"error": "invalid body"})
			}
			return e.JSON(200, req)
		})
		return se.Next()
	})
}
