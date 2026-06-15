package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"strconv"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		// Ensure products collection exists
		_, err := se.App.FindCollectionByNameOrId("products")
		if err != nil {
			// Create collection
			collection := core.NewBaseCollection("products")
			collection.Fields.Add(
				&core.TextField{Name: "sku"},
				&core.TextField{Name: "name"},
				&core.NumberField{Name: "price"},
			)

			if err := se.App.Save(collection); err != nil {
				return fmt.Errorf("failed to create products collection: %w", err)
			}
		}

		se.Router.POST("/api/import/products", func(e *core.RequestEvent) error {
			file, _, err := e.Request.FormFile("file")
			if err != nil {
				return e.JSON(400, map[string]interface{}{
					"inserted": 0,
					"errors": []map[string]interface{}{
						{"row": 0, "reason": "Missing or invalid file"},
					},
				})
			}
			defer file.Close()

			reader := csv.NewReader(file)
			records, err := reader.ReadAll()
			if err != nil {
				return e.JSON(400, map[string]interface{}{
					"inserted": 0,
					"errors": []map[string]interface{}{
						{"row": 0, "reason": "Invalid CSV format"},
					},
				})
			}

			if len(records) < 1 {
				return e.JSON(400, map[string]interface{}{
					"inserted": 0,
					"errors": []map[string]interface{}{
						{"row": 0, "reason": "Empty CSV"},
					},
				})
			}

			// Validate header
			header := records[0]
			if len(header) < 3 || header[0] != "sku" || header[1] != "name" || header[2] != "price" {
				return e.JSON(400, map[string]interface{}{
					"inserted": 0,
					"errors": []map[string]interface{}{
						{"row": 0, "reason": "Invalid CSV header"},
					},
				})
			}

			type rowError struct {
				Row    int    `json:"row"`
				Reason string `json:"reason"`
			}
			var rowErrors []rowError

			insertedCount := 0
			seenSkus := make(map[string]bool)

			txErr := e.App.RunInTransaction(func(txApp core.App) error {
				collection, err := txApp.FindCollectionByNameOrId("products")
				if err != nil {
					return fmt.Errorf("failed to find collection: %w", err)
				}

				for i := 1; i < len(records); i++ {
					row := records[i]
					if len(row) < 3 {
						rowErrors = append(rowErrors, rowError{Row: i, Reason: "Invalid row length"})
						continue
					}

					sku := row[0]
					name := row[1]
					priceStr := row[2]

					// Validation: price must be > 0
					price, err := strconv.ParseFloat(priceStr, 64)
					if err != nil || price <= 0 {
						rowErrors = append(rowErrors, rowError{Row: i, Reason: "Invalid price"})
						continue
					}

					// Validation: sku must be unique within the uploaded file
					if seenSkus[sku] {
						rowErrors = append(rowErrors, rowError{Row: i, Reason: "Duplicate SKU in file"})
						continue
					}
					seenSkus[sku] = true

					// Validation: sku must not already exist in the products collection
					existing, err := txApp.FindFirstRecordByData("products", "sku", sku)
					if err == nil && existing != nil {
						rowErrors = append(rowErrors, rowError{Row: i, Reason: "SKU already exists"})
						continue
					}

					// Insert
					record := core.NewRecord(collection)
					record.Set("sku", sku)
					record.Set("name", name)
					record.Set("price", price)

					if err := txApp.Save(record); err != nil {
						rowErrors = append(rowErrors, rowError{Row: i, Reason: fmt.Sprintf("Failed to save: %v", err)})
					} else {
						insertedCount++
					}
				}

				if len(rowErrors) > 0 {
					return fmt.Errorf("validation failed")
				}

				return nil
			})

			if txErr != nil && len(rowErrors) > 0 {
				return e.JSON(400, map[string]interface{}{
					"inserted": 0,
					"errors":   rowErrors,
				})
			} else if txErr != nil {
				return e.JSON(500, map[string]interface{}{
					"inserted": 0,
					"errors": []map[string]interface{}{
						{"row": 0, "reason": txErr.Error()},
					},
				})
			}

			return e.JSON(200, map[string]interface{}{
				"inserted": insertedCount,
				"errors":   []interface{}{},
			})
		}).Bind(apis.RequireSuperuserAuth())
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
