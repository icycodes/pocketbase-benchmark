package main

import (
	"encoding/json"
	"errors"
	"log"
	"math"
	"math/rand"
	"net/http"
	"strings"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

// transferRequest is the expected JSON body for POST /api/wallets/transfer.
type transferRequest struct {
	FromID string  `json:"fromId"`
	ToID   string  `json:"toId"`
	Amount float64 `json:"amount"`
}

// transferResponse is returned on success.
type transferResponse struct {
	FromBalance float64 `json:"fromBalance"`
	ToBalance   float64 `json:"toBalance"`
}

// isSQLiteBusy returns true when err is (or wraps) an SQLite SQLITE_BUSY /
// SQLITE_LOCKED error so we can safely retry.
func isSQLiteBusy(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "sqlite_busy") ||
		strings.Contains(msg, "sqlite_locked") ||
		strings.Contains(msg, "database is locked") ||
		strings.Contains(msg, "database table is locked")
}

// withRetry executes fn inside app.RunInTransaction, retrying up to maxAttempts
// times when SQLite signals BUSY/LOCKED. It uses truncated exponential
// back-off with jitter so concurrent goroutines don't pile up in lock-step.
func withRetry(app *pocketbase.PocketBase, maxAttempts int, fn func(txApp core.App) error) error {
	const baseDelay = 50 * time.Millisecond
	var lastErr error
	for attempt := 0; attempt < maxAttempts; attempt++ {
		lastErr = app.RunInTransaction(func(txApp core.App) error {
			return fn(txApp)
		})
		if lastErr == nil {
			return nil
		}
		// Only retry on transient locking errors; propagate everything else.
		if !isSQLiteBusy(lastErr) {
			return lastErr
		}
		// Exponential back-off: 50ms, 100ms, 200ms, 400ms … capped at 1.6 s,
		// plus up to 25 ms of random jitter to spread retries.
		delay := time.Duration(math.Min(
			float64(baseDelay)*math.Pow(2, float64(attempt)),
			float64(1600*time.Millisecond),
		))
		delay += time.Duration(rand.Int63n(int64(25 * time.Millisecond)))
		time.Sleep(delay)
	}
	return lastErr
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			// ── 1. Authentication ────────────────────────────────────────────
			authRecord := e.Auth
			if authRecord == nil {
				return e.JSON(http.StatusUnauthorized, map[string]string{
					"error": "authentication required",
				})
			}

			// ── 2. Parse & validate request body ────────────────────────────
			var req transferRequest
			if err := json.NewDecoder(e.Request.Body).Decode(&req); err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": "invalid JSON body",
				})
			}
			if req.FromID == "" || req.ToID == "" {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": "fromId and toId are required",
				})
			}
			if req.FromID == req.ToID {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": "fromId and toId must be different",
				})
			}
			if req.Amount <= 0 {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": "amount must be positive",
				})
			}

			// ── 3. Execute transfer inside a retried transaction ─────────────
			var result transferResponse
			var insufficientFunds bool

			err := withRetry(app, 5, func(txApp core.App) error {
				insufficientFunds = false // reset on each attempt

				// Lock wallets in a deterministic id-ascending order to
				// prevent deadlocks when two goroutines transfer in opposite
				// directions simultaneously.
				firstID, secondID := req.FromID, req.ToID
				if firstID > secondID {
					firstID, secondID = secondID, firstID
				}

				// Fetch first wallet (lower id).
				first, err := txApp.FindRecordById("wallets", firstID)
				if err != nil {
					return err
				}
				// Fetch second wallet (higher id).
				second, err := txApp.FindRecordById("wallets", secondID)
				if err != nil {
					return err
				}

				// Map back to from/to regardless of the locking order.
				fromWallet := first
				toWallet := second
				if req.FromID == secondID {
					fromWallet = second
					toWallet = first
				}

				fromBalance := fromWallet.GetFloat("balance")
				toBalance := toWallet.GetFloat("balance")

				if fromBalance < req.Amount {
					insufficientFunds = true
					// Return a sentinel so RunInTransaction rolls back.
					return errors.New("insufficient funds")
				}

				newFromBalance := fromBalance - req.Amount
				newToBalance := toBalance + req.Amount

				fromWallet.Set("balance", newFromBalance)
				if err := txApp.Save(fromWallet); err != nil {
					return err
				}

				toWallet.Set("balance", newToBalance)
				if err := txApp.Save(toWallet); err != nil {
					return err
				}

				// Insert audit row in the transfers collection.
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

				result = transferResponse{
					FromBalance: newFromBalance,
					ToBalance:   newToBalance,
				}
				return nil
			})

			if insufficientFunds {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"error": "insufficient funds",
				})
			}
			if err != nil {
				return e.JSON(http.StatusInternalServerError, map[string]string{
					"error": err.Error(),
				})
			}

			return e.JSON(http.StatusOK, result)
		})

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
