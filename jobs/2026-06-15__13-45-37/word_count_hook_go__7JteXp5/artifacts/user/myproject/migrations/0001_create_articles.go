package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		collection := core.NewBaseCollection("articles")

		collection.Fields.Add(
			&core.TextField{Name: "title", Required: true, Max: 200},
			&core.TextField{Name: "content"},
			&core.NumberField{Name: "word_count", OnlyInt: true},
			&core.NumberField{Name: "reading_time_minutes", OnlyInt: true},
		)

		return app.Save(collection)
	}, func(app core.App) error {
		c, err := app.FindCollectionByNameOrId("articles")
		if err != nil {
			return err
		}
		return app.Delete(c)
	})
}
