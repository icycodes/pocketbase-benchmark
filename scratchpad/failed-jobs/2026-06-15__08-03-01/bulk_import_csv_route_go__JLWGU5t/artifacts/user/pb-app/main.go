package main

import (
	"encoding/csv"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/import-csv", importCSVHandler)
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func importCSVHandler(e *core.RequestEvent) error {
	// Validate collection field
	collectionName := e.Request.FormValue("collection")
	if collectionName == "" {
		return e.JSON(http.StatusBadRequest, map[string]string{"error": "Missing collection field"})
	}

	// Validate file field
	file, _, err := e.Request.FormFile("file")
	if err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{"error": "Missing or invalid file field"})
	}
	defer file.Close()

	// Parse CSV
	csvReader := csv.NewReader(file)
	records, err := csvReader.ReadAll()
	if err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid CSV format"})
	}

	if len(records) < 1 {
		return e.JSON(http.StatusBadRequest, map[string]string{"error": "CSV must contain a header row"})
	}

	// Find the target collection
	collection, err := e.App.FindCollectionByNameOrId(collectionName)
	if err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{"error": "Collection not found"})
	}

	// First row is the header with field names
	headers := records[0]
	imported := 0

	// Insert each data row as a new record
	for _, row := range records[1:] {
		record := core.NewRecord(collection)
		for i, header := range headers {
			if i < len(row) {
				record.Set(header, row[i])
			}
		}
		if err := e.App.Save(record); err != nil {
			continue
		}
		imported++
	}

	return e.JSON(http.StatusOK, map[string]int{"imported": imported})
}