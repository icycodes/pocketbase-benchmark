package migrations

import (
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/daos"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/models/schema"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(db dbx.Builder) error {
		dao := daos.New(db)

		collection := &models.Collection{
			Name: "configs",
			Type: models.CollectionTypeBase,
			ListRule: types.Pointer(""),
			ViewRule: types.Pointer(""),
			Schema: schema.NewSchema(
				&schema.SchemaField{
					Name:     "key",
					Type:     schema.FieldTypeText,
					Required: true,
				},
				&schema.SchemaField{
					Name:     "value",
					Type:     schema.FieldTypeText,
				},
			),
		}

		if err := dao.SaveCollection(collection); err != nil {
			return err
		}

		r1 := models.NewRecord(collection)
		r1.Set("key", "site_name")
		r1.Set("value", "My Site")
		if err := dao.SaveRecord(r1); err != nil {
			return err
		}

		r2 := models.NewRecord(collection)
		r2.Set("key", "maintenance_mode")
		r2.Set("value", "false")
		if err := dao.SaveRecord(r2); err != nil {
			return err
		}

		return nil
	}, func(db dbx.Builder) error {
		dao := daos.New(db)
		col, err := dao.FindCollectionByNameOrId("configs")
		if err != nil {
			return err
		}
		return dao.DeleteCollection(col)
	})
}
