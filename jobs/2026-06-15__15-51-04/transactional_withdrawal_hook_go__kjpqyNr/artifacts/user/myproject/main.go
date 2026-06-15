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
		amount := e.Record.GetFloat("amount")
		if amount <= 0 {
			return e.BadRequestError("Amount must be greater than 0.", nil)
		}

		walletId := e.Record.GetString("wallet")
		if walletId == "" {
			return e.BadRequestError("Wallet is required.", nil)
		}

		originalApp := e.App

		err := originalApp.RunInTransaction(func(txApp core.App) error {
			wallet, err := txApp.FindRecordById("wallets", walletId)
			if err != nil {
				return e.BadRequestError("Wallet not found.", nil)
			}

			currentBalance := wallet.GetFloat("balance")
			if currentBalance < amount {
				return e.BadRequestError("Insufficient balance.", nil)
			}

			wallet.Set("balance", currentBalance-amount)
			if err := txApp.Save(wallet); err != nil {
				return e.BadRequestError("Failed to update wallet balance.", nil)
			}

			e.App = txApp
			defer func() { e.App = originalApp }()

			return e.Next()
		})

		return err
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
