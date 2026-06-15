package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	_ "myproject/migrations"
)

func main() {
	app := pocketbase.New()

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	// Hook: validate and atomically process withdrawal record creation requests.
	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		amount := e.Record.GetFloat("amount")
		walletId := e.Record.GetString("wallet")

		// Validate: amount must be > 0
		if amount <= 0 {
			return e.BadRequestError("amount must be greater than 0", nil)
		}

		// Validate: wallet field must be present
		if walletId == "" {
			return e.BadRequestError("wallet is required", nil)
		}

		// Run everything inside a single transaction so balance debit and
		// withdrawal creation are atomic.
		return e.App.RunInTransaction(func(txApp core.App) error {
			// Load the wallet inside the transaction.
			wallet, err := txApp.FindRecordById("wallets", walletId)
			if err != nil {
				return e.BadRequestError("wallet not found", nil)
			}

			// Validate: wallet must have sufficient balance.
			balance := wallet.GetFloat("balance")
			if balance < amount {
				return e.BadRequestError("insufficient wallet balance", nil)
			}

			// Debit the wallet.
			wallet.Set("balance", balance-amount)
			if err := txApp.Save(wallet); err != nil {
				return err
			}

			// Re-point e.App to the transactional app so that the downstream
			// chain (which persists the withdrawal record) also runs inside
			// the same transaction.
			originalApp := e.App
			e.App = txApp
			defer func() { e.App = originalApp }()

			// Propagate to PocketBase's default save logic.
			return e.Next()
		})
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
