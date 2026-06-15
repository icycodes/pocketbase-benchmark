package main

import (
	"errors"
	"log"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
)

func main() {
	app := pocketbase.New()

	// Bootstrap collections on startup
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// 1. Check and create wallets collection
		wallets, err := e.App.FindCollectionByNameOrId("wallets")
		if err != nil {
			wallets = core.NewBaseCollection("wallets")
			wallets.ListRule = types.Pointer("")
			wallets.ViewRule = types.Pointer("")
			wallets.CreateRule = types.Pointer("")
			wallets.UpdateRule = types.Pointer("")
			wallets.DeleteRule = types.Pointer("")

			wallets.Fields.Add(&core.NumberField{
				Name:     "balance",
				Required: true,
			})
			wallets.Fields.Add(&core.AutodateField{
				Name:     "created",
				OnCreate: true,
			})
			wallets.Fields.Add(&core.AutodateField{
				Name:     "updated",
				OnCreate: true,
				OnUpdate: true,
			})

			if err := e.App.Save(wallets); err != nil {
				return err
			}
		}

		// 2. Check and create withdrawals collection
		withdrawals, err := e.App.FindCollectionByNameOrId("withdrawals")
		if err != nil {
			withdrawals = core.NewBaseCollection("withdrawals")
			withdrawals.ListRule = types.Pointer("")
			withdrawals.ViewRule = types.Pointer("")
			withdrawals.CreateRule = types.Pointer("")
			withdrawals.UpdateRule = types.Pointer("")
			withdrawals.DeleteRule = types.Pointer("")

			withdrawals.Fields.Add(&core.RelationField{
				Name:         "wallet_id",
				Required:     true,
				CollectionId: wallets.Id,
				MaxSelect:    1,
			})
			withdrawals.Fields.Add(&core.NumberField{
				Name:     "amount",
				Required: true,
			})
			withdrawals.Fields.Add(&core.AutodateField{
				Name:     "created",
				OnCreate: true,
			})
			withdrawals.Fields.Add(&core.AutodateField{
				Name:     "updated",
				OnCreate: true,
				OnUpdate: true,
			})

			if err := e.App.Save(withdrawals); err != nil {
				return err
			}
		}

		return e.Next()
	})

	// Register event hook on withdrawals creation
	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		originalApp := e.App
		txErr := e.App.RunInTransaction(func(txApp core.App) error {
			e.App = txApp

			walletId := e.Record.GetString("wallet_id")
			amount := e.Record.GetFloat("amount")

			if walletId == "" {
				return apis.NewBadRequestError("wallet_id is required", nil)
			}
			if amount <= 0 {
				return apis.NewBadRequestError("amount must be greater than 0", nil)
			}

			// Perform atomic update inside the transaction
			res, err := txApp.DB().NewQuery(
				"UPDATE wallets SET balance = balance - {:amount} WHERE id = {:id} AND balance >= {:amount}",
			).Bind(dbx.Params{
				"amount": amount,
				"id":     walletId,
			}).Execute()
			if err != nil {
				return err
			}

			rowsAffected, err := res.RowsAffected()
			if err != nil {
				return err
			}

			if rowsAffected == 0 {
				// Check if the wallet exists
				var exists int
				err = txApp.DB().NewQuery(
					"SELECT COUNT(*) FROM wallets WHERE id = {:id}",
				).Bind(dbx.Params{"id": walletId}).Row(&exists)
				if err != nil {
					return err
				}

				if exists == 0 {
					return apis.NewNotFoundError("Wallet not found", nil)
				}
				return apis.NewBadRequestError("Insufficient funds", errors.New("insufficient funds"))
			}

			// Proceed with creating the withdrawal record
			if err := e.Next(); err != nil {
				return err
			}

			return nil
		})

		e.App = originalApp
		return txErr
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
