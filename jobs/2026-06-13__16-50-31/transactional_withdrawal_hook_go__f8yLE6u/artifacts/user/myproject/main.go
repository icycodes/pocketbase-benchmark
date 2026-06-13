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

	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		// 1. Read fields
		walletId := e.Record.GetString("wallet")
		amount := e.Record.GetFloat("amount")

		// 2. Validate presence of amount field in request body
		info, err := e.RequestInfo()
		if err != nil {
			return e.BadRequestError("Failed to read request info", err)
		}

		if _, exists := info.Body["amount"]; !exists {
			return e.BadRequestError("Amount field must be present", nil)
		}

		// 3. Validate amount strictly greater than 0
		if amount <= 0 {
			return e.BadRequestError("Amount must be strictly greater than 0", nil)
		}

		// 4. Validate presence of wallet field
		if walletId == "" {
			return e.BadRequestError("Wallet field is required", nil)
		}

		// 5. Run transaction
		return e.App.RunInTransaction(func(txApp core.App) error {
			// Inside transaction, find the wallet
			wallet, err := txApp.FindRecordById("wallets", walletId)
			if err != nil {
				return e.BadRequestError("Wallet not found", err)
			}

			// Validate wallet balance
			balance := wallet.GetFloat("balance")
			if balance < amount {
				return e.BadRequestError("Insufficient funds", nil)
			}

			// Decrease wallet balance
			wallet.Set("balance", balance-amount)
			if err := txApp.Save(wallet); err != nil {
				return err
			}

			// Temporarily re-point e.App to txApp for the downstream chain
			originalApp := e.App
			e.App = txApp
			defer func() {
				e.App = originalApp
			}()

			// Propagate the chain
			return e.Next()
		})
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
