package main

import (
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"

	_ "app/migrations"
)

func main() {
	app := pocketbase.New()

	// Intercept withdrawal creation requests and atomically deduct balance.
	//
	// Concurrency strategy:
	//   • RunInTransaction routes to NonconcurrentDB which has MaxOpenConns=1,
	//     so concurrent write transactions are serialised through a single
	//     SQLite connection.
	//   • Inside the transaction we use a single atomic UPDATE … WHERE balance
	//     >= amount statement.  If 0 rows are affected the balance is
	//     insufficient and we return a 400 error, rolling back the transaction
	//     so the withdrawal record is never persisted.
	//   • SQLite WAL busy_timeout(10000) ensures waiting goroutines retry for
	//     up to 10 s instead of failing immediately.
	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		amount := e.Record.GetFloat("amount")
		walletID := e.Record.GetString("wallet_id")

		if walletID == "" {
			return apis.NewBadRequestError("wallet_id is required", nil)
		}
		if amount <= 0 {
			return apis.NewBadRequestError("amount must be greater than zero", nil)
		}

		// Run the balance deduction inside a serialised transaction so that
		// concurrent requests cannot both read the same balance and both
		// succeed when only one should.
		txErr := e.App.RunInTransaction(func(txApp core.App) error {
			// Atomically deduct balance only when sufficient funds exist.
			// Using raw SQL UPDATE with a WHERE guard makes the check-and-deduct
			// a single atomic operation — no separate SELECT is needed.
			result, err := txApp.DB().NewQuery(
				"UPDATE wallets SET balance = balance - {:amount} WHERE id = {:id} AND balance >= {:amount}",
			).Bind(map[string]any{
				"amount": amount,
				"id":     walletID,
			}).Execute()
			if err != nil {
				return err
			}

			rowsAffected, err := result.RowsAffected()
			if err != nil {
				return err
			}

			if rowsAffected == 0 {
				// Either the wallet doesn't exist or insufficient funds.
				// Distinguish the two cases to return a meaningful error.
				wallet, findErr := txApp.FindRecordById("wallets", walletID)
				if findErr != nil || wallet == nil {
					return apis.NewBadRequestError("wallet not found", nil)
				}
				return apis.NewBadRequestError("insufficient funds", map[string]any{
					"balance": wallet.GetFloat("balance"),
					"amount":  amount,
				})
			}

			return nil
		})

		if txErr != nil {
			return txErr
		}

		// Balance deducted successfully — proceed to persist the withdrawal.
		return e.Next()
	})

	// Compensate: if saving the withdrawal record fails after the balance was
	// already deducted, roll back the balance decrement.
	app.OnRecordAfterCreateError("withdrawals").BindFunc(func(e *core.RecordErrorEvent) error {
		walletID := e.Record.GetString("wallet_id")
		amount := e.Record.GetFloat("amount")

		if walletID == "" || amount <= 0 {
			return e.Next()
		}

		// Best-effort balance restore — log but don't mask the original error.
		restoreErr := e.App.RunInTransaction(func(txApp core.App) error {
			_, err := txApp.DB().NewQuery(
				"UPDATE wallets SET balance = balance + {:amount} WHERE id = {:id}",
			).Bind(map[string]any{
				"amount": amount,
				"id":     walletID,
			}).Execute()
			return err
		})
		if restoreErr != nil {
			e.App.Logger().Error(
				"failed to restore wallet balance after withdrawal save error",
				"walletId", walletID,
				"amount", amount,
				"error", restoreErr,
			)
		}

		return e.Next()
	})

	// Serve with proper HTTP status mapping for ApiError.
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.GET("/healthz", func(re *core.RequestEvent) error {
			return re.JSON(http.StatusOK, map[string]string{"status": "ok"})
		})
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
