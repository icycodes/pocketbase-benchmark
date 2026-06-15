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

	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		amount := e.Record.GetFloat("amount")
		if amount <= 0 {
			return e.BadRequestError("Amount must be strictly greater than 0", nil)
		}

		walletId := e.Record.GetString("wallet")
		if walletId == "" {
			return e.BadRequestError("Wallet is required", nil)
		}

		return e.App.RunInTransaction(func(txApp core.App) error {
			wallet, err := txApp.FindRecordById("wallets", walletId)
			if err != nil {
				return e.BadRequestError("Wallet not found", err)
			}

			balance := wallet.GetFloat("balance")
			if balance < amount {
				return e.BadRequestError("Insufficient funds", nil)
			}

			wallet.Set("balance", balance-amount)
			if err := txApp.Save(wallet); err != nil {
				return err
			}

			originalApp := e.App
			e.App = txApp
			defer func() {
				e.App = originalApp
			}()

			return e.Next()
		})
	})

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
