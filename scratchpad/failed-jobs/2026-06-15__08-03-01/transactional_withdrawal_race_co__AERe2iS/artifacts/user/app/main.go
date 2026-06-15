package main

import (
	"errors"
	"fmt"
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

func main() {
	app := pocketbase.New()

	// Set up collections on bootstrap
	app.OnBootstrap().BindFunc(func(e *core.BootstrapEvent) error {
		if err := e.Next(); err != nil {
			return err
		}
		return setupCollections(e.App)
	})

	// Hook into withdrawal creation to deduct balance atomically
	app.OnRecordCreateRequest("withdrawals").BindFunc(func(e *core.RecordRequestEvent) error {
		walletID := e.Record.GetString("wallet_id")
		amount := e.Record.GetFloat("amount")

		if walletID == "" {
			return router.NewBadRequestError("wallet_id is required", nil)
		}
		if amount <= 0 {
			return router.NewBadRequestError("amount must be greater than 0", nil)
		}

		err := e.App.RunInTransaction(func(txApp core.App) error {
			// Use raw SQL for atomic balance deduction to prevent race conditions.
			// The WHERE clause ensures the balance never drops below zero,
			// and the UPDATE is atomic at the SQLite level.
			result, err := txApp.DB().NewQuery(
				"UPDATE wallets SET balance = balance - {:amount} WHERE id = {:id} AND balance >= {:amount}",
			).Bind(map[string]any{
				"amount": amount,
				"id":     walletID,
			}).Execute()
			if err != nil {
				return fmt.Errorf("failed to deduct balance: %w", err)
			}

			rowsAffected, err := result.RowsAffected()
			if err != nil {
				return fmt.Errorf("failed to check rows affected: %w", err)
			}

			if rowsAffected == 0 {
				return errors.New("insufficient funds")
			}

			return nil
		})

		if err != nil {
			return router.NewBadRequestError(err.Error(), nil)
		}

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

// setupCollections creates the wallets and withdrawals collections if they don't exist.
func setupCollections(app core.App) error {
	// Create wallets collection if not exists
	walletsCol, err := app.FindCollectionByNameOrId("wallets")
	if err != nil || walletsCol == nil {
		walletsCol = core.NewBaseCollection("wallets")
		walletsCol.Fields.Add(&core.NumberField{
			Name:     "balance",
			Required: true,
		})

		if err := app.Save(walletsCol); err != nil {
			return fmt.Errorf("failed to create wallets collection: %w", err)
		}
	}

	// Create withdrawals collection if not exists
	withdrawalsCol, err := app.FindCollectionByNameOrId("withdrawals")
	if err != nil || withdrawalsCol == nil {
		withdrawalsCol = core.NewBaseCollection("withdrawals")
		withdrawalsCol.Fields.Add(&core.RelationField{
			Name:         "wallet_id",
			CollectionId: walletsCol.Id,
			Required:     true,
			MaxSelect:    1,
		})
		withdrawalsCol.Fields.Add(&core.NumberField{
			Name:     "amount",
			Required: true,
		})

		if err := app.Save(withdrawalsCol); err != nil {
			return fmt.Errorf("failed to create withdrawals collection: %w", err)
		}
	}

	return nil
}