package main

import (
	"errors"
	"fmt"
	"log"
	"math"
	"net/http"
	"strings"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type transferRequest struct {
	FromID string  `json:"fromId"`
	ToID   string  `json:"toId"`
	Amount float64 `json:"amount"`
}

type transferResponse struct {
	FromBalance float64 `json:"fromBalance"`
	ToBalance   float64 `json:"toBalance"`
}

type insufficientFundsError struct {
	currentBalance float64
	requested      float64
}

func (e *insufficientFundsError) Error() string {
	return fmt.Sprintf("insufficient funds: balance is %.2f, requested %.2f", e.currentBalance, e.requested)
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", transferHandler(app)).
			Bind(apis.RequireAuth())

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func transferHandler(app core.App) func(e *core.RequestEvent) error {
	return func(e *core.RequestEvent) error {
		var req transferRequest
		if err := e.BindBody(&req); err != nil {
			return router.NewBadRequestError("Invalid request body", err)
		}

		if req.FromID == "" || req.ToID == "" {
			return router.NewBadRequestError("fromId and toId are required", nil)
		}
		if req.FromID == req.ToID {
			return router.NewBadRequestError("fromId and toId must be different", nil)
		}
		if req.Amount <= 0 {
			return router.NewBadRequestError("amount must be positive", nil)
		}

		var resp transferResponse
		var lastErr error

		delay := 50 * time.Millisecond
		maxDelay := 1600 * time.Millisecond

		for attempt := 0; attempt < 5; attempt++ {
			if attempt > 0 {
				time.Sleep(delay)
				delay = time.Duration(math.Min(float64(delay)*2, float64(maxDelay)))
			}

			lastErr = app.RunInTransaction(func(txApp core.App) error {
				// Reset response for each attempt
				resp = transferResponse{}

				// Lock wallets in consistent id-ascending order to prevent deadlocks
				firstID, secondID := req.FromID, req.ToID
				if secondID < firstID {
					firstID, secondID = secondID, firstID
				}

				// Read wallets in ascending ID order first
				_, err := txApp.FindRecordById("wallets", firstID)
				if err != nil {
					return fmt.Errorf("wallet %s not found: %w", firstID, err)
				}
				_, err = txApp.FindRecordById("wallets", secondID)
				if err != nil {
					return fmt.Errorf("wallet %s not found: %w", secondID, err)
				}

				// Now read the actual from/to wallets
				fromWallet, err := txApp.FindRecordById("wallets", req.FromID)
				if err != nil {
					return fmt.Errorf("source wallet not found: %w", err)
				}
				toWallet, err := txApp.FindRecordById("wallets", req.ToID)
				if err != nil {
					return fmt.Errorf("destination wallet not found: %w", err)
				}

				fromBalance := fromWallet.GetFloat("balance")
				toBalance := toWallet.GetFloat("balance")

				if fromBalance < req.Amount {
					return &insufficientFundsError{
						currentBalance: fromBalance,
						requested:      req.Amount,
					}
				}

				fromWallet.Set("balance", fromBalance-req.Amount)
				toWallet.Set("balance", toBalance+req.Amount)

				if err := txApp.Save(fromWallet); err != nil {
					return fmt.Errorf("failed to update source wallet: %w", err)
				}
				if err := txApp.Save(toWallet); err != nil {
					return fmt.Errorf("failed to update destination wallet: %w", err)
				}

				// Create audit row in transfers collection
				collection, err := txApp.FindCollectionByNameOrId("transfers")
				if err != nil {
					return fmt.Errorf("transfers collection not found: %w", err)
				}
				transfer := core.NewRecord(collection)
				transfer.Set("fromId", req.FromID)
				transfer.Set("toId", req.ToID)
				transfer.Set("amount", req.Amount)
				if err := txApp.Save(transfer); err != nil {
					return fmt.Errorf("failed to save transfer record: %w", err)
				}

				resp.FromBalance = fromBalance - req.Amount
				resp.ToBalance = toBalance + req.Amount

				return nil
			})

			if lastErr == nil {
				return e.JSON(http.StatusOK, resp)
			}

			// If it's a business logic error (insufficient funds), don't retry
			var insuffErr *insufficientFundsError
			if errors.As(lastErr, &insuffErr) {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": insuffErr.Error(),
				})
			}

			// If it's not a SQLITE_BUSY error, don't retry
			if !isBusyError(lastErr) {
				break
			}
		}

		return lastErr
	}
}

func isBusyError(err error) bool {
	if err == nil {
		return false
	}
	errMsg := err.Error()
	return strings.Contains(errMsg, "SQLITE_BUSY") ||
		strings.Contains(errMsg, "database is locked") ||
		strings.Contains(errMsg, "cannot start a transaction") ||
		strings.Contains(errMsg, "cannot acquire a database lock")
}