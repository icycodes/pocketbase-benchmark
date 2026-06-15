package main

import (
	"errors"
	"log"
	"math/rand"
	"strings"
	"time"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

type TransferReq struct {
	FromId string  `json:"fromId"`
	ToId   string  `json:"toId"`
	Amount float64 `json:"amount"`
}

var ErrInsufficientFunds = errors.New("insufficient funds")

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			auth := e.Auth
			if auth == nil {
				return e.JSON(401, map[string]any{"error": "unauthorized"})
			}

			req := new(TransferReq)
			if err := e.BindBody(req); err != nil {
				return e.JSON(400, map[string]any{"error": "invalid body"})
			}

			if req.FromId == req.ToId {
				return e.JSON(400, map[string]any{"error": "cannot transfer to same wallet"})
			}
			if req.Amount <= 0 {
				return e.JSON(400, map[string]any{"error": "amount must be positive"})
			}

			var finalFromBalance, finalToBalance float64

			maxAttempts := 5
			baseDelay := 50 * time.Millisecond

			for attempt := 0; attempt < maxAttempts; attempt++ {
				err := app.RunInTransaction(func(txApp core.App) error {
					firstId, secondId := req.FromId, req.ToId
					if firstId > secondId {
						firstId, secondId = secondId, firstId
					}

					// Lock first
					_, err := txApp.DB().NewQuery("UPDATE wallets SET id=id WHERE id={:id}").Bind(dbx.Params{"id": firstId}).Execute()
					if err != nil {
						return err
					}

					// Lock second
					_, err = txApp.DB().NewQuery("UPDATE wallets SET id=id WHERE id={:id}").Bind(dbx.Params{"id": secondId}).Execute()
					if err != nil {
						return err
					}

					fromRecord, err := txApp.FindRecordById("wallets", req.FromId)
					if err != nil {
						return err
					}

					toRecord, err := txApp.FindRecordById("wallets", req.ToId)
					if err != nil {
						return err
					}

					fromBalance := fromRecord.GetFloat("balance")
					if fromBalance < req.Amount {
						return ErrInsufficientFunds
					}

					toBalance := toRecord.GetFloat("balance")

					finalFromBalance = fromBalance - req.Amount
					finalToBalance = toBalance + req.Amount

					fromRecord.Set("balance", finalFromBalance)
					toRecord.Set("balance", finalToBalance)

					if err := txApp.Save(fromRecord); err != nil {
						return err
					}
					if err := txApp.Save(toRecord); err != nil {
						return err
					}

					transferCollection, err := txApp.FindCollectionByNameOrId("transfers")
					if err != nil {
						return err
					}

					transferRecord := core.NewRecord(transferCollection)
					transferRecord.Set("fromId", req.FromId)
					transferRecord.Set("toId", req.ToId)
					transferRecord.Set("amount", req.Amount)

					if err := txApp.Save(transferRecord); err != nil {
						return err
					}

					return nil
				})

				if err == nil {
					return e.JSON(200, map[string]any{
						"fromBalance": finalFromBalance,
						"toBalance":   finalToBalance,
					})
				}

				if err == ErrInsufficientFunds {
					return e.JSON(400, map[string]any{"error": "insufficient funds"})
				}

				if strings.Contains(err.Error(), "database is locked") || strings.Contains(err.Error(), "busy") {
					if attempt < maxAttempts-1 {
						delay := baseDelay * (1 << attempt)
						jitter := time.Duration(rand.Int63n(int64(delay) / 2))
						time.Sleep(delay + jitter)
						continue
					}
				}
				return e.JSON(500, map[string]any{"error": err.Error()})
			}

			return e.JSON(500, map[string]any{"error": "max retries exceeded"})
		})
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
