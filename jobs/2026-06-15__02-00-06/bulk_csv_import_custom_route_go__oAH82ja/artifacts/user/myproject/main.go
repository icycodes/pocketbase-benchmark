package main

import (
	"database/sql"
	"encoding/csv"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

type RowError struct {
	Row    int    `json:"row"`
	Reason string `json:"reason"`
}

func main() {
	app := pocketbase.New()

	// Bootstrap collection and register custom route
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		// 1. Ensure the "products" collection exists
		collection, err := se.App.FindCollectionByNameOrId("products")
		if err != nil {
			// Collection doesn't exist, create it
			collection = core.NewBaseCollection("products")
			collection.Fields.Add(
				&core.TextField{
					Name:     "sku",
					Required: true,
				},
				&core.TextField{
					Name:     "name",
					Required: true,
				},
				&core.NumberField{
					Name:     "price",
					Required: true,
				},
			)

			if err := se.App.Save(collection); err != nil {
				return err
			}
			log.Println("Created 'products' collection successfully")
		} else {
			_ = collection
		}

		// 2. Register POST /api/import/products route
		se.Router.POST("/api/import/products", func(re *core.RequestEvent) error {
			// Parse multipart form (max 32MB)
			if err := re.Request.ParseMultipartForm(32 << 20); err != nil {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Failed to parse multipart form: " + err.Error()},
					},
				})
			}

			// Retrieve file from form field
			file, _, err := re.Request.FormFile("file")
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Missing or invalid 'file' field"},
					},
				})
			}
			defer file.Close()

			// Parse CSV
			reader := csv.NewReader(file)
			header, err := reader.Read()
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Failed to read CSV header: " + err.Error()},
					},
				})
			}

			// Validate header columns
			if len(header) < 3 || header[0] != "sku" || header[1] != "name" || header[2] != "price" {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Invalid CSV header. Expected 'sku,name,price'"},
					},
				})
			}

			// Read all data rows
			records, err := reader.ReadAll()
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Failed to read CSV data rows: " + err.Error()},
					},
				})
			}

			skuInFile := make(map[string]bool)
			var validationErrors []RowError
			var insertedCount int

			// Execute inserts in a single transaction
			txErr := se.App.RunInTransaction(func(txApp core.App) error {
				for i, row := range records {
					rowNum := i + 1

					if len(row) < 3 {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "Row has insufficient columns",
						})
						continue
					}

					sku := strings.TrimSpace(row[0])
					name := strings.TrimSpace(row[1])
					priceStr := strings.TrimSpace(row[2])

					if sku == "" {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "sku cannot be empty",
						})
						continue
					}
					if name == "" {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "name cannot be empty",
						})
						continue
					}

					price, err := strconv.ParseFloat(priceStr, 64)
					if err != nil {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "price must be a valid number",
						})
						continue
					}
					if price <= 0 {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "price must be > 0",
						})
						continue
					}

					if skuInFile[sku] {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "sku must be unique within the uploaded file",
						})
						continue
					}
					skuInFile[sku] = true

					// Check if SKU exists in database
					existing, err := txApp.FindFirstRecordByData("products", "sku", sku)
					if err == nil && existing != nil {
						validationErrors = append(validationErrors, RowError{
							Row:    rowNum,
							Reason: "sku must not already exist in the products collection",
						})
						continue
					} else if err != nil && !errors.Is(err, sql.ErrNoRows) {
						return err
					}

					// Prepare and insert product record
					prodCollection, err := txApp.FindCollectionByNameOrId("products")
					if err != nil {
						return err
					}

					record := core.NewRecord(prodCollection)
					record.Set("sku", sku)
					record.Set("name", name)
					record.Set("price", price)

					if err := txApp.Save(record); err != nil {
						return err
					}
					insertedCount++
				}

				if len(validationErrors) > 0 {
					return errors.New("validation failed")
				}

				return nil
			})

			if len(validationErrors) > 0 {
				return re.JSON(http.StatusBadRequest, map[string]any{
					"inserted": 0,
					"errors":   validationErrors,
				})
			}

			if txErr != nil {
				return re.JSON(http.StatusInternalServerError, map[string]any{
					"inserted": 0,
					"errors": []RowError{
						{Row: 0, Reason: "Database transaction error: " + txErr.Error()},
					},
				})
			}

			return re.JSON(http.StatusOK, map[string]any{
				"inserted": insertedCount,
				"errors":   []RowError{},
			})
		}).Bind(apis.RequireSuperuserAuth())

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
