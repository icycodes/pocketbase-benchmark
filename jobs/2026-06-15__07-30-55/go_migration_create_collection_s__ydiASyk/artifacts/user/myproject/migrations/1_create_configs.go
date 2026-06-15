package migrations

import (
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/daos"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/models/schema"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(db dbx.Builder) error {
		dao := daos.New(db)

		// Create the configs collection
		collection := &models.Collection{}
		collection.MarkAsNew()
		collection.Name = "configs"
		collection.Type = models.CollectionTypeBase

		// Set public read access (empty string = allow everyone)
		collection.ListRule = types.Pointer("")
		collection.ViewRule = types.Pointer("")

		// Define fields: key (required text) and value (text)
		collection.Schema = schema.NewSchema(
			&schema.SchemaField{
				Name:     "key",
				Type:     schema.FieldTypeText,
				Required: true,
				Options:  &schema.TextOptions{},
			},
			&schema.SchemaField{
				Name:     "value",
				Type:     schema.FieldTypeText,
				Required: false,
				Options:  &schema.TextOptions{},
			},
		)

		if err := dao.SaveCollection(collection); err != nil {
			return err
		}

		// Seed record 1: site_name
		record1 := models.NewRecord(collection)
		record1.Set("key", "site_name")
		record1.Set("value", "My Site")
		if err := dao.SaveRecord(record1); err != nil {
			return err
		}

		// Seed record 2: maintenance_mode
		record2 := models.NewRecord(collection)
		record2.Set("key", "maintenance_mode")
		record2.Set("value", "false")
		if err := dao.SaveRecord(record2); err != nil {
			return err
		}

		return nil
	}, func(db dbx.Builder) error {
		dao := daos.New(db)

		collection, err := dao.FindCollectionByNameOrId("configs")
		if err != nil {
			return err
		}

		return dao.DeleteCollection(collection)
	})
}
