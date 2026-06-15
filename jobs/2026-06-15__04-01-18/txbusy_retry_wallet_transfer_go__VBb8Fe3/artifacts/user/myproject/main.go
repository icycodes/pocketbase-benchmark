package main

import (
	"log"
	"math"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", transferHandler).
			Bind(apis.RequireAuth())

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

type transferRequest struct {
	FromID string  `json:"fromId"`
	ToID   string  `json:"toId"`
	Amount float64 `json:"amount"`
}

type transferResponse struct {
	FromBalance float64 `json:"fromBalance"`
	ToBalance   float64 `json:"toBalance"`
}

func transferHandler(e *core.RequestEvent) error {
	var req transferRequest
	if err := e.BindBody(&req); err != nil {
		return e.BadRequestError("invalid request body", err)
	}

	if req.FromID == "" || req.ToID == "" {
		return e.BadRequestError("fromId and toId are required", nil)
	}
	if req.FromID == req.ToID {
		return e.BadRequestError("fromId and toId must be different", nil)
	}
	if req.Amount <= 0 {
		return e.BadRequestError("amount must be positive", nil)
	}

	// Order wallet IDs to avoid deadlocks (consistent lock ordering).
	firstID, secondID := req.FromID, req.ToID
	if firstID > secondID {
		firstID, secondID = secondID, firstID
	}

	var resp transferResponse
	var lastErr error

	for attempt := 0; attempt < 5; attempt++ {
		if attempt > 0 {
			// Exponential backoff: 50ms, 100ms, 200ms, 400ms, 800ms
			backoff := time.Duration(50*math.Pow(2, float64(attempt-1))) * time.Millisecond
			time.Sleep(backoff)
		}

		err := e.App.RunInTransaction(func(txApp core.App) error {
			// Lock wallets in consistent id-ascending order.
			wallet1, err := txApp.FindRecordById("wallets", firstID)
			if err != nil {
				return err
			}
			wallet2, err := txApp.FindRecordById("wallets", secondID)
			if err != nil {
				return err
			}

			// Determine which wallet is from and which is to.
			var fromWallet, toWallet *core.Record
			if firstID == req.FromID {
				fromWallet, toWallet = wallet1, wallet2
			} else {
				fromWallet, toWallet = wallet2, wallet1
			}

			fromBalance := fromWallet.GetFloat("balance")
			if fromBalance < req.Amount {
				return e.BadRequestError("insufficient funds", nil)
			}

			// Update balances.
			fromWallet.Set("balance", fromBalance-req.Amount)
			toWallet.Set("balance", toWallet.GetFloat("balance")+req.Amount)

			if err := txApp.Save(fromWallet); err != nil {
				return err
			}
			if err := txApp.Save(toWallet); err != nil {
				return err
			}

			// Create audit record in transfers collection.
			transfersCollection, err := txApp.FindCollectionByNameOrId("transfers")
			if err != nil {
				return err
			}

			transferRecord := core.NewRecord(transfersCollection)
			transferRecord.Set("fromId", req.FromID)
			transferRecord.Set("toId", req.ToID)
			transferRecord.Set("amount", req.Amount)

			if err := txApp.Save(transferRecord); err != nil {
				return err
			}

			resp.FromBalance = fromBalance - req.Amount
			resp.ToBalance = toWallet.GetFloat("balance")

			return nil
		})

		if err == nil {
			return e.JSON(200, resp)
		}

		// Check if it's a user-facing error (not a retryable one).
		if apiErr, ok := err.(*core.RequestEvent); ok {
			_ = apiErr
		}

		// If it's a BadRequestError (like insufficient funds), don't retry.
		if isBadRequestError(err) {
			return err
		}

		lastErr = err
		// Otherwise it's likely SQLITE_BUSY, retry.
	}

	// All retries exhausted.
	if lastErr != nil {
		return e.InternalServerError("transfer failed after retries", lastErr)
	}
	return e.InternalServerError("transfer failed", nil)
}

func isBadRequestError(err error) bool {
	type badRequestError interface {
		StatusCode() int
	}
	if bre, ok := err.(badRequestError); ok {
		return bre.StatusCode() == 400
	}
	return false
}
