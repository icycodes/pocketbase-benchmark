package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// ── wallets collection ────────────────────────────────────────
		wallets := core.NewBaseCollection("wallets")
		wallets.ListRule = nil
		wallets.ViewRule = nil
		wallets.CreateRule = nil
		wallets.UpdateRule = nil
		wallets.DeleteRule = nil

		wallets.Fields.Add(&core.NumberField{
			Name:     "balance",
			Required: true,
			Min:      func() *float64 { v := float64(0); return &v }(),
		})

		if err := app.Save(wallets); err != nil {
			return err
		}

		// ── withdrawals collection ─────────────────────────────────────
		withdrawals := core.NewBaseCollection("withdrawals")
		withdrawals.ListRule = nil
		withdrawals.ViewRule = nil
		withdrawals.CreateRule = nil
		withdrawals.UpdateRule = nil
		withdrawals.DeleteRule = nil

		withdrawals.Fields.Add(&core.RelationField{
			Name:         "wallet_id",
			Required:     true,
			CollectionId: wallets.Id,
			MaxSelect:    1,
		})

		withdrawals.Fields.Add(&core.NumberField{
			Name:     "amount",
			Required: true,
			Min:      func() *float64 { v := float64(0); return &v }(),
		})

		return app.Save(withdrawals)
	}, func(app core.App) error {
		// down – remove collections in reverse order
		for _, name := range []string{"withdrawals", "wallets"} {
			col, err := app.FindCollectionByNameOrId(name)
			if err != nil {
				return err
			}
			if err := app.Delete(col); err != nil {
				return err
			}
		}
		return nil
	})
}
