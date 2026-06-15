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
		info, err := e.RequestInfo()
		if err != nil {
			return e.BadRequestError("failed to parse request info", err)
		}

		// Validate amount is present
		amountVal, ok := info.Body["amount"]
		if !ok || amountVal == nil {
			return e.BadRequestError("amount field is required", nil)
		}

		// Validate amount is strictly greater than 0
		amount := e.Record.GetFloat("amount")
		if amount <= 0 {
			return e.BadRequestError("amount must be strictly greater than 0", nil)
		}

		// Validate wallet is present
		walletIdVal, ok := info.Body["wallet"]
		if !ok || walletIdVal == nil {
			return e.BadRequestError("wallet field is required", nil)
		}

		walletId := e.Record.GetString("wallet")
		if walletId == "" {
			return e.BadRequestError("wallet field is required", nil)
		}

		// Run in transaction
		txErr := e.App.RunInTransaction(func(txApp core.App) error {
			// Find the wallet inside the transaction
			wallet, err := txApp.FindRecordById("wallets", walletId)
			if err != nil {
				// Reject with 400 Bad Request if wallet does not exist
				return e.BadRequestError("wallet not found", nil)
			}

			// Validate wallet has sufficient balance
			balance := wallet.GetFloat("balance")
			if balance < amount {
				return e.BadRequestError("insufficient balance", nil)
			}

			// Decrease balance
			wallet.Set("balance", balance - amount)
			if err := txApp.Save(wallet); err != nil {
				return err
			}

			// Temporarily re-point e.App to txApp so the downstream hook propagation runs inside the transaction
			originalApp := e.App
			e.App = txApp
			defer func() {
				e.App = originalApp
			}()

			// Propagate the request chain
			return e.Next()
		})

		return txErr
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
