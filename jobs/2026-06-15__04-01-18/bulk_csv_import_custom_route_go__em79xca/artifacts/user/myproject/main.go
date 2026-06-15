package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"strconv"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
)

func main() {
	app := pocketbase.New()

	// -------------------------------------------------------------------
	// Ensure the "products" collection exists after bootstrap
	// -------------------------------------------------------------------
	app.OnBootstrap().Bind(&hook.Handler[*core.BootstrapEvent]{
		Func: func(e *core.BootstrapEvent) error {
			// Check if the collection already exists
			existing, err := e.App.FindCollectionByNameOrId("products")
			if err == nil && existing != nil {
				return e.Next()
			}

			// Create the "products" base collection
			collection := core.NewBaseCollection("products")

			// Add fields: sku (text), name (text), price (number)
			collection.Fields.Add(&core.TextField{
				Name:     "sku",
				Required: true,
			})
			collection.Fields.Add(&core.TextField{
				Name:     "name",
				Required: true,
			})
			collection.Fields.Add(&core.NumberField{
				Name:     "price",
				Required: true,
			})

			if err := e.App.Save(collection); err != nil {
				return fmt.Errorf("failed to create products collection: %w", err)
			}

			return e.Next()
		},
	})

	// -------------------------------------------------------------------
	// Register the custom route POST /api/import/products
	// -------------------------------------------------------------------
	app.OnServe().Bind(&hook.Handler[*core.ServeEvent]{
		Func: func(e *core.ServeEvent) error {
			// Create a sub-group at /api/import with superuser auth middleware
			group := e.Router.Group("/api/import")
			group.Bind(apis.RequireSuperuserAuth())

			group.POST("/products", func(re *core.RequestEvent) error {
				return handleImportProducts(re)
			})

			return e.Next()
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

// -----------------------------------------------------------------------
// CSV import row validation error
// -----------------------------------------------------------------------
type importError struct {
	Row    int    `json:"row"`
	Reason string `json:"reason"`
}

// -----------------------------------------------------------------------
// POST /api/import/products handler
// -----------------------------------------------------------------------
func handleImportProducts(e *core.RequestEvent) error {
	// Find the uploaded file named "file"
	files, err := e.FindUploadedFiles("file")
	if err != nil {
		return e.BadRequestError("Failed to read uploaded file", err)
	}
	if len(files) == 0 {
		return e.BadRequestError("No file uploaded", nil)
	}

	uploadedFile := files[0]

	// Open the file reader
	fileReader, err := uploadedFile.Reader.Open()
	if err != nil {
		return e.BadRequestError("Failed to open uploaded file", err)
	}
	defer fileReader.Close()

	// Read the CSV
	reader := csv.NewReader(fileReader)
	reader.TrimLeadingSpace = true

	// Read header
	header, err := reader.Read()
	if err != nil {
		return e.BadRequestError("Failed to read CSV header", err)
	}

	// Validate header: must be "sku,name,price"
	expectedHeader := []string{"sku", "name", "price"}
	if len(header) != 3 ||
		strings.TrimSpace(header[0]) != expectedHeader[0] ||
		strings.TrimSpace(header[1]) != expectedHeader[1] ||
		strings.TrimSpace(header[2]) != expectedHeader[2] {
		return e.BadRequestError(
			"Invalid CSV header, expected: sku,name,price",
			nil,
		)
	}

	// Parse all data rows (1-based, header is row 0)
	type rowData struct {
		rowNum int
		sku    string
		name   string
		price  float64
	}

	var rows []rowData
	var validationErrors []importError

	// Track SKU uniqueness within the file
	seenSKUs := make(map[string]bool)

	rowNum := 1 // data rows start at 1 (after header)
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: fmt.Sprintf("Failed to read CSV row: %v", err),
			})
			rowNum++
			continue
		}

		if len(record) < 3 {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: "Row has fewer than 3 columns",
			})
			rowNum++
			continue
		}

		sku := strings.TrimSpace(record[0])
		name := strings.TrimSpace(record[1])
		priceStr := strings.TrimSpace(record[2])

		// Validate price is a valid number and > 0
		price, err := strconv.ParseFloat(priceStr, 64)
		if err != nil {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: fmt.Sprintf("Invalid price value: %q", priceStr),
			})
			rowNum++
			continue
		}

		if price <= 0 {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: fmt.Sprintf("Price must be greater than 0, got: %v", price),
			})
			rowNum++
			continue
		}

		// Validate SKU is not empty
		if sku == "" {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: "SKU must not be empty",
			})
			rowNum++
			continue
		}

		// Validate SKU uniqueness within the file
		if seenSKUs[sku] {
			validationErrors = append(validationErrors, importError{
				Row:    rowNum,
				Reason: fmt.Sprintf("Duplicate SKU %q within the uploaded file", sku),
			})
			rowNum++
			continue
		}
		seenSKUs[sku] = true

		rows = append(rows, rowData{
			rowNum: rowNum,
			sku:    sku,
			name:   name,
			price:  price,
		})
		rowNum++
	}

	// If there are pre-validation errors, return them immediately
	if len(validationErrors) > 0 {
		return e.JSON(400, map[string]any{
			"inserted": 0,
			"errors":   validationErrors,
		})
	}

	// Check SKU uniqueness against the database and insert all rows in a transaction
	collection, err := e.App.FindCollectionByNameOrId("products")
	if err != nil {
		return e.InternalServerError("Failed to find products collection", err)
	}

	// Run everything inside a single transaction
	err = e.App.RunInTransaction(func(txApp core.App) error {
		for _, row := range rows {
			// Check if SKU already exists in the database
			existing, findErr := txApp.FindFirstRecordByData(collection, "sku", row.sku)
			if findErr == nil && existing != nil {
				validationErrors = append(validationErrors, importError{
					Row:    row.rowNum,
					Reason: fmt.Sprintf("SKU %q already exists in the database", row.sku),
				})
				continue
			}

			// Create new record
			record := core.NewRecord(collection)
			record.Set("sku", row.sku)
			record.Set("name", row.name)
			record.Set("price", row.price)

			if saveErr := txApp.Save(record); saveErr != nil {
				validationErrors = append(validationErrors, importError{
					Row:    row.rowNum,
					Reason: fmt.Sprintf("Failed to save record: %v", saveErr),
				})
			}
		}

		// If any errors occurred, return an error to trigger rollback
		if len(validationErrors) > 0 {
			return fmt.Errorf("validation errors: %d rows failed", len(validationErrors))
		}

		return nil
	})

	if err != nil {
		// Transaction was rolled back due to validation errors
		return e.JSON(400, map[string]any{
			"inserted": 0,
			"errors":   validationErrors,
		})
	}

	// Success
	return e.JSON(200, map[string]any{
		"inserted": len(rows),
		"errors":   []importError{},
	})
}
