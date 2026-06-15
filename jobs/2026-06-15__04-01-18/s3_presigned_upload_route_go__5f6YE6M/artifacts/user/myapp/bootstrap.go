package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/daos"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/models/schema"
	"github.com/pocketbase/pocketbase/tools/types"
)

func bootstrapCollections(app *pocketbase.PocketBase) error {
	dao := app.Dao()

	// Ensure users collection exists (PocketBase creates it by default, but let's make sure)
	_, err := dao.FindCollectionByNameOrId("users")
	if err != nil {
		log.Printf("INFO: users collection not found, it should be auto-created by PocketBase")
	}

	// Create pending_upload collection if it doesn't exist
	if _, err := dao.FindCollectionByNameOrId("pending_upload"); err != nil {
		log.Printf("INFO: creating pending_upload collection")
		pendingCollection := &models.Collection{
			Name: "pending_upload",
			Type: models.CollectionTypeBase,
			Schema: schema.NewSchema(
				&schema.SchemaField{
					Name:     "user",
					Type:     schema.FieldTypeRelation,
					Required: true,
					Options: &schema.RelationOptions{
						CollectionId: "", // will be set after finding users collection
						MaxSelect:    types.Pointer(1),
					},
				},
				&schema.SchemaField{
					Name:     "key",
					Type:     schema.FieldTypeText,
					Required: true,
					Unique:   true,
				},
				&schema.SchemaField{
					Name:     "expires_at",
					Type:     schema.FieldTypeDate,
					Required: true,
				},
			),
		}

		// Set the relation collection id
		if usersCollection, err := dao.FindCollectionByNameOrId("users"); err == nil {
			for _, field := range pendingCollection.Schema.Fields() {
				if field.Name == "user" {
					field.Options.(*schema.RelationOptions).CollectionId = usersCollection.Id
				}
			}
		}

		if err := dao.SaveCollection(pendingCollection); err != nil {
			return err
		}
	}

	// Create uploads collection if it doesn't exist
	if _, err := dao.FindCollectionByNameOrId("uploads"); err != nil {
		log.Printf("INFO: creating uploads collection")
		uploadsCollection := &models.Collection{
			Name: "uploads",
			Type: models.CollectionTypeBase,
			Schema: schema.NewSchema(
				&schema.SchemaField{
					Name:     "user",
					Type:     schema.FieldTypeRelation,
					Required: true,
					Options: &schema.RelationOptions{
						CollectionId: "",
						MaxSelect:    types.Pointer(1),
					},
				},
				&schema.SchemaField{
					Name:     "key",
					Type:     schema.FieldTypeText,
					Required: true,
					Unique:   true,
				},
			),
		}

		// Set the relation collection id
		if usersCollection, err := dao.FindCollectionByNameOrId("users"); err == nil {
			for _, field := range uploadsCollection.Schema.Fields() {
				if field.Name == "user" {
					field.Options.(*schema.RelationOptions).CollectionId = usersCollection.Id
				}
			}
		}

		if err := dao.SaveCollection(uploadsCollection); err != nil {
			return err
		}
	}

	return nil
}

func seedData(app *pocketbase.PocketBase) error {
	dao := app.Dao()

	// Seed superuser
	superusersCollection, err := dao.FindCollectionByNameOrId(core.CollectionNameSuperusers)
	if err != nil {
		return err
	}

	existingAdmin, _ := dao.FindAuthRecordByEmail(superusersCollection.Name, "admin@example.com")
	if existingAdmin == nil {
		log.Printf("INFO: creating superuser admin@example.com")
		adminRecord := models.NewRecord(superusersCollection)
		adminRecord.SetEmail("admin@example.com")
		adminRecord.SetPassword("1234567890")
		if err := dao.SaveRecord(adminRecord); err != nil {
			log.Printf("ERROR: failed to create superuser: %v", err)
		}
	}

	// Seed regular auth users
	usersCollection, err := dao.FindCollectionByNameOrId("users")
	if err != nil {
		return err
	}

	// user@example.com / password1234
	existingUser, _ := dao.FindAuthRecordByEmail(usersCollection.Name, "user@example.com")
	if existingUser == nil {
		log.Printf("INFO: creating user user@example.com")
		userRecord := models.NewRecord(usersCollection)
		userRecord.SetEmail("user@example.com")
		userRecord.SetPassword("password1234")
		if err := dao.SaveRecord(userRecord); err != nil {
			log.Printf("ERROR: failed to create user: %v", err)
		}
	}

	// other@example.com / password1234
	existingOther, _ := dao.FindAuthRecordByEmail(usersCollection.Name, "other@example.com")
	if existingOther == nil {
		log.Printf("INFO: creating user other@example.com")
		otherRecord := models.NewRecord(usersCollection)
		otherRecord.SetEmail("other@example.com")
		otherRecord.SetPassword("password1234")
		if err := dao.SaveRecord(otherRecord); err != nil {
			log.Printf("ERROR: failed to create user other@example.com: %v", err)
		}
	}

	return nil
}

var _ = daos.New(nil)
