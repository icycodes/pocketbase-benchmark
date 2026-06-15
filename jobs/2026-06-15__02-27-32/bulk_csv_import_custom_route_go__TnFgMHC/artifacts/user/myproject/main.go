package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

// importError describes a single row-level validation failure.
type importError struct {
	Row    int    `json:"row"`
	Reason string `json:"reason"`
}

// importResponse is the JSON body returned by the import route.
type importResponse struct {
	Inserted int           `json:"inserted"`
	Errors   []importError `json:"errors"`
}

func main() {
	app := pocketbase.New()

	// ------------------------------------------------------------------ //
	// Bootstrap: ensure the "products" collection exists on startup.      //
	// ------------------------------------------------------------------ //
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		if err := ensureProductsCollection(se.App); err != nil {
			return err
		}
		registerImportRoute(se)
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

// ensureProductsCollection creates the "products" base collection when it does
// not yet exist, or leaves it untouched when it already does.
func ensureProductsCollection(app core.App) error {
	// Check if the collection already exists.
	existing, _ := app.FindCollectionByNameOrId("products")
	if existing != nil {
		return nil
	}

	collection := core.NewBaseCollection("products")

	skuField := &core.TextField{}
	skuField.Name = "sku"
	skuField.Required = true

	nameField := &core.TextField{}
	nameField.Name = "name"
	nameField.Required = true

	priceField := &core.NumberField{}
	priceField.Name = "price"
	priceField.Required = true

	collection.Fields.Add(skuField, nameField, priceField)

	// Set up a unique index on sku.
	collection.AddIndex("idx_products_sku_unique", true, "sku", "")

	return app.Save(collection)
}

// registerImportRoute wires the POST /api/import/products handler.
func registerImportRoute(se *core.ServeEvent) {
	se.Router.POST("/api/import/products", func(e *core.RequestEvent) error {
		// ---------------------------------------------------------------- //
		// 1. Authentication & authorisation checks                          //
		// ---------------------------------------------------------------- //
		authRecord := e.Auth

		if authRecord == nil {
			return e.JSON(http.StatusUnauthorized, map[string]string{
				"message": "unauthorized",
			})
		}

		// Only superusers (admins) may call this endpoint.
		if !authRecord.IsSuperuser() {
			return e.JSON(http.StatusForbidden, map[string]string{
				"message": "forbidden – superuser access required",
			})
		}

		// ---------------------------------------------------------------- //
		// 2. Parse the multipart file                                       //
		// ---------------------------------------------------------------- //
		uploadedFile, _, err := e.Request.FormFile("file")
		if err != nil {
			return e.JSON(http.StatusBadRequest, map[string]string{
				"message": "missing or unreadable 'file' field",
			})
		}
		defer uploadedFile.Close()

		reader := csv.NewReader(uploadedFile)

		// Read & discard the header row.
		header, err := reader.Read()
		if err != nil {
			return e.JSON(http.StatusBadRequest, map[string]string{
				"message": "failed to read CSV header",
			})
		}

		// Validate header columns (order-independent).
		headerMap := make(map[string]int, len(header))
		for i, col := range header {
			headerMap[col] = i
		}
		for _, required := range []string{"sku", "name", "price"} {
			if _, ok := headerMap[required]; !ok {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"message": fmt.Sprintf("CSV header missing required column: %s", required),
				})
			}
		}

		skuIdx := headerMap["sku"]
		nameIdx := headerMap["name"]
		priceIdx := headerMap["price"]

		// ---------------------------------------------------------------- //
		// 3. Parse every data row and validate locally                      //
		// ---------------------------------------------------------------- //
		type productRow struct {
			sku   string
			name  string
			price float64
		}

		var rows []productRow
		var validationErrors []importError
		seenSKUs := make(map[string]bool)
		rowNum := 0

		for {
			record, err := reader.Read()
			if err == io.EOF {
				break
			}
			if err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{
					"message": fmt.Sprintf("failed to read CSV row: %v", err),
				})
			}
			rowNum++

			sku := record[skuIdx]
			name := record[nameIdx]
			priceStr := record[priceIdx]

			// Validate price > 0.
			price, parseErr := strconv.ParseFloat(priceStr, 64)
			if parseErr != nil || price <= 0 {
				validationErrors = append(validationErrors, importError{
					Row:    rowNum,
					Reason: fmt.Sprintf("price must be a number greater than 0 (got %q)", priceStr),
				})
			}

			// Validate sku uniqueness within the file.
			if seenSKUs[sku] {
				validationErrors = append(validationErrors, importError{
					Row:    rowNum,
					Reason: fmt.Sprintf("duplicate sku %q within the uploaded file", sku),
				})
			} else {
				seenSKUs[sku] = true
			}

			rows = append(rows, productRow{sku: sku, name: name, price: price})
		}

		// ---------------------------------------------------------------- //
		// 4. Check sku uniqueness against the existing DB records           //
		//    (only when there are no local errors so far, to keep errors    //
		//     focused – but we still report all DB-level conflicts).        //
		// ---------------------------------------------------------------- //
		collection, err := se.App.FindCollectionByNameOrId("products")
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{
				"message": "could not find products collection",
			})
		}

		for i, row := range rows {
			existing, findErr := se.App.FindFirstRecordByData("products", "sku", row.sku)
			if findErr == nil && existing != nil {
				validationErrors = append(validationErrors, importError{
					Row:    i + 1,
					Reason: fmt.Sprintf("sku %q already exists in the products collection", row.sku),
				})
			}
		}

		// If any validation errors were collected, return 400 immediately.
		if len(validationErrors) > 0 {
			return writeJSON(e, http.StatusBadRequest, importResponse{
				Inserted: 0,
				Errors:   validationErrors,
			})
		}

		// ---------------------------------------------------------------- //
		// 5. Insert all rows inside a single transaction                    //
		// ---------------------------------------------------------------- //
		inserted := 0

		txErr := se.App.RunInTransaction(func(txApp core.App) error {
			for _, row := range rows {
				record := core.NewRecord(collection)
				record.Set("sku", row.sku)
				record.Set("name", row.name)
				record.Set("price", row.price)

				if saveErr := txApp.Save(record); saveErr != nil {
					return fmt.Errorf("failed to save row with sku %q: %w", row.sku, saveErr)
				}
				inserted++
			}
			return nil
		})

		if txErr != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{
				"message": txErr.Error(),
			})
		}

		return writeJSON(e, http.StatusOK, importResponse{
			Inserted: inserted,
			Errors:   []importError{},
		})
	})
}

// writeJSON marshals v and writes it as JSON with the given status code.
func writeJSON(e *core.RequestEvent, status int, v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	e.Response.Header().Set("Content-Type", "application/json")
	e.Response.WriteHeader(status)
	_, _ = e.Response.Write(b)
	return nil
}

