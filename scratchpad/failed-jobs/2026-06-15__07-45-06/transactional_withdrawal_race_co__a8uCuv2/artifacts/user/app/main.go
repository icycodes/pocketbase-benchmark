package main

import (
    "log"

    "github.com/pocketbase/pocketbase"
    "github.com/pocketbase/pocketbase/core"
    "github.com/pocketbase/pocketbase/apis"
)

func main() {
    app := pocketbase.New()

    app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
        return e.App.RunInTransaction(func(txApp core.App) error {
            oldApp := e.App
            e.App = txApp
            defer func() { e.App = oldApp }()

            walletId := e.Record.GetString("wallet_id")
            amount := e.Record.GetFloat("amount")

            wallet, err := txApp.FindRecordById("wallets", walletId)
            if err != nil {
                return apis.NewBadRequestError("Wallet not found", err)
            }

            balance := wallet.GetFloat("balance")
            if balance < amount {
                return apis.NewBadRequestError("Insufficient funds", nil)
            }

            wallet.Set("balance", balance - amount)
            if err := txApp.Save(wallet); err != nil {
                return err
            }

            return e.Next()
        })
    })

    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
