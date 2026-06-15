package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/models/schema"
)

type SubscriptionResponse struct {
	Status string `json:"status"`
}

func main() {
	app := pocketbase.New()

	app.OnBeforeServe().Add(func(e *core.ServeEvent) error {
		dao := app.Dao()
		if _, err := dao.FindCollectionByNameOrId("posts"); err != nil {
			collection := &models.Collection{
				Name: "posts",
				Type: models.CollectionTypeBase,
				CreateRule: nil, // wait, nil means admin only, let's use string pointer
			}
			emptyStr := ""
			collection.CreateRule = &emptyStr
			collection.ViewRule = &emptyStr
			collection.ListRule = &emptyStr
			collection.UpdateRule = &emptyStr
			collection.DeleteRule = &emptyStr
			collection.Schema = schema.NewSchema(
				&schema.SchemaField{
					Name: "title",
					Type: schema.FieldTypeText,
				},
				&schema.SchemaField{
					Name: "author",
					Type: schema.FieldTypeText,
				},
			)
			if err := dao.SaveCollection(collection); err != nil {
				return err
			}
		}
		return nil
	})

	app.OnRecordBeforeCreateRequest("posts").Add(func(e *core.RecordCreateEvent) error {
		authorID := e.Record.GetString("author")
		if authorID == "" {
			return apis.NewBadRequestError("Missing author", nil)
		}

		resp, err := http.Get(fmt.Sprintf("http://localhost:8080/api/subscription?userId=%s", authorID))
		if err != nil {
			return apis.NewBadRequestError("Failed to check subscription", err)
		}
		defer resp.Body.Close()

		var subResp SubscriptionResponse
		if err := json.NewDecoder(resp.Body).Decode(&subResp); err != nil {
			return apis.NewBadRequestError("Invalid subscription response", err)
		}

		if subResp.Status != "active" {
			return apis.NewBadRequestError("User does not have an active subscription", nil)
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
