package main

import (
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"modernc.org/sqlite"
)

// LockManager handles fine-grained row-level locking at the application level.
type LockManager struct {
	mu    sync.Mutex
	locks map[string]*sync.Mutex
}

func NewLockManager() *LockManager {
	return &LockManager{
		locks: make(map[string]*sync.Mutex),
	}
}

func (lm *LockManager) getLock(id string) *sync.Mutex {
	lm.mu.Lock()
	defer lm.mu.Unlock()
	if l, exists := lm.locks[id]; exists {
		return l
	}
	l := &sync.Mutex{}
	lm.locks[id] = l
	return l
}

func (lm *LockManager) LockPair(id1, id2 string) func() {
	if id1 == id2 {
		l := lm.getLock(id1)
		l.Lock()
		return func() { l.Unlock() }
	}

	if id1 > id2 {
		id1, id2 = id2, id1
	}

	l1 := lm.getLock(id1)
	l2 := lm.getLock(id2)

	l1.Lock()
	l2.Lock()

	return func() {
		l2.Unlock()
		l1.Unlock()
	}
}

type TransferRequest struct {
	FromId string  `json:"fromId"`
	ToId   string  `json:"toId"`
	Amount float64 `json:"amount"`
}

func isSqliteBusy(err error) bool {
	if err == nil {
		return false
	}
	var sqliteErr *sqlite.Error
	if errors.As(err, &sqliteErr) {
		code := sqliteErr.Code()
		// SQLITE_BUSY (5), SQLITE_LOCKED (6), or related busy/locked subcodes
		if code == 5 || code == 6 || code == 261 || code == 517 || code == 773 {
			return true
		}
	}
	errStr := err.Error()
	return strings.Contains(errStr, "database is locked") ||
		strings.Contains(errStr, "SQLITE_BUSY") ||
		strings.Contains(errStr, "SQLITE_LOCKED") ||
		strings.Contains(errStr, "locked")
}

func main() {
	app := pocketbase.New()
	lockManager := NewLockManager()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		// Register POST /api/wallets/transfer here.
		se.Router.POST("/api/wallets/transfer", func(e *core.RequestEvent) error {
			// 1. Unmarshal request body
			var req TransferRequest
			if err := e.BindBody(&req); err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request body"})
			}

			// 2. Validate request parameters
			fromId := strings.TrimSpace(req.FromId)
			toId := strings.TrimSpace(req.ToId)
			amount := req.Amount

			if fromId == "" || toId == "" {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "fromId and toId are required"})
			}
			if amount <= 0 {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "Amount must be greater than zero"})
			}
			if fromId == toId {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "Cannot transfer to the same wallet"})
			}

			// 3. Application-level fine-grained locking in consistent ID-ascending order
			unlock := lockManager.LockPair(fromId, toId)
			defer unlock()

			// 4. Retry loop on SQLITE_BUSY with exponential backoff (up to 5 attempts, 50ms..1.6s)
			var fromBalance, toBalance float64
			var txErr error

			backoff := 50 * time.Millisecond
			for attempt := 1; attempt <= 5; attempt++ {
				txErr = se.App.RunInTransaction(func(txApp core.App) error {
					// Fetch wallets in consistent id-ascending order inside transaction
					var wallet1, wallet2 *core.Record
					var err error

					id1, id2 := fromId, toId
					if id1 > id2 {
						id1, id2 = id2, id1
					}

					wallet1, err = txApp.FindRecordById("wallets", id1)
					if err != nil {
						return fmt.Errorf("wallet_not_found: %s", id1)
					}
					wallet2, err = txApp.FindRecordById("wallets", id2)
					if err != nil {
						return fmt.Errorf("wallet_not_found: %s", id2)
					}

					var fromWallet, toWallet *core.Record
					if fromId == id1 {
						fromWallet = wallet1
						toWallet = wallet2
					} else {
						fromWallet = wallet2
						toWallet = wallet1
					}

					// Check insufficient funds
					currentFromBalance := fromWallet.GetFloat("balance")
					if currentFromBalance < amount {
						return fmt.Errorf("insufficient_funds")
					}

					// Update balances
					fromWallet.Set("balance", currentFromBalance-amount)
					toWallet.Set("balance", toWallet.GetFloat("balance")+amount)

					if err := txApp.SaveNoValidate(fromWallet); err != nil {
						return err
					}
					if err := txApp.SaveNoValidate(toWallet); err != nil {
						return err
					}

					// Write audit row in transfers collection
					transfersCollection, err := txApp.FindCollectionByNameOrId("transfers")
					if err != nil {
						return err
					}
					transferRecord := core.NewRecord(transfersCollection)
					transferRecord.Set("fromId", fromId)
					transferRecord.Set("toId", toId)
					transferRecord.Set("amount", amount)

					if err := txApp.SaveNoValidate(transferRecord); err != nil {
						return err
					}

					fromBalance = fromWallet.GetFloat("balance")
					toBalance = toWallet.GetFloat("balance")
					return nil
				})

				if txErr == nil {
					break
				}

				// If it's insufficient funds or wallet not found, do not retry!
				if txErr.Error() == "insufficient_funds" || strings.HasPrefix(txErr.Error(), "wallet_not_found") {
					break
				}

				// Check if it's SQLITE_BUSY / locked error
				if isSqliteBusy(txErr) && attempt < 5 {
					time.Sleep(backoff)
					backoff *= 2
					if backoff > 1600*time.Millisecond {
						backoff = 1600 * time.Millisecond
					}
					continue
				}

				// Other errors or we ran out of attempts
				break
			}

			// Handle transaction result
			if txErr != nil {
				if txErr.Error() == "insufficient_funds" {
					return e.JSON(http.StatusBadRequest, map[string]string{"error": "Insufficient funds"})
				}
				if strings.HasPrefix(txErr.Error(), "wallet_not_found") {
					return e.JSON(http.StatusNotFound, map[string]string{"error": txErr.Error()})
				}
				return e.JSON(http.StatusInternalServerError, map[string]string{"error": txErr.Error()})
			}

			// Return success response
			return e.JSON(http.StatusOK, map[string]interface{}{
				"fromBalance": fromBalance,
				"toBalance":   toBalance,
			})
		}).Bind(apis.RequireAuth())

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
