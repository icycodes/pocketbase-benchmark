package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"

	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		open := types.Pointer("")

		// --- wallets ---
		wallets := core.NewBaseCollection("wallets")
		wallets.Fields.Add(
			&core.TextField{Name: "owner", Required: true, Max: 200},
			&core.NumberField{Name: "balance"},
		)
		wallets.ListRule = open
		wallets.ViewRule = open
		wallets.CreateRule = open
		wallets.UpdateRule = open
		wallets.DeleteRule = open
		if err := app.Save(wallets); err != nil {
			return err
		}

		// --- withdrawals ---
		withdrawals := core.NewBaseCollection("withdrawals")
		withdrawals.Fields.Add(
			&core.RelationField{
				Name:         "wallet",
				Required:     true,
				CollectionId: wallets.Id,
				MaxSelect:    1,
			},
			&core.NumberField{Name: "amount"},
			&core.TextField{Name: "note", Max: 500},
		)
		withdrawals.ListRule = open
		withdrawals.ViewRule = open
		withdrawals.CreateRule = open
		withdrawals.UpdateRule = open
		withdrawals.DeleteRule = open
		return app.Save(withdrawals)
	}, func(app core.App) error {
		for _, name := range []string{"withdrawals", "wallets"} {
			collection, err := app.FindCollectionByNameOrId(name)
			if err != nil {
				continue
			}
			if err := app.Delete(collection); err != nil {
				return err
			}
		}
		return nil
	})
}
