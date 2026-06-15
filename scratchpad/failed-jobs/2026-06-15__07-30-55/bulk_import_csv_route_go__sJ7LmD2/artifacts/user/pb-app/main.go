package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/import-csv", func(re *core.RequestEvent) error {
			// Validate collection name
			collectionName := re.Request.FormValue("collection")
			if collectionName == "" {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "missing required field: collection",
				})
			}

			// Validate uploaded file
			file, _, err := re.Request.FormFile("file")
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "missing or invalid file: " + err.Error(),
				})
			}
			defer file.Close()

			// Parse CSV
			reader := csv.NewReader(file)
			records, err := reader.ReadAll()
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "invalid CSV format: " + err.Error(),
				})
			}

			if len(records) < 1 {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "CSV file is empty",
				})
			}

			headers := records[0]
			if len(headers) == 0 {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "CSV header row is empty",
				})
			}

			// Fetch the target collection
			collection, err := re.App.FindCollectionByNameOrId(collectionName)
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "collection not found: " + err.Error(),
				})
			}

			// Insert each data row as a new record
			imported := 0
			for i, row := range records[1:] {
				if len(row) != len(headers) {
					return re.JSON(http.StatusBadRequest, map[string]string{
						"error": fmt.Sprintf("row %d has %d columns, expected %d", i+1, len(row), len(headers)),
					})
				}

				record := core.NewRecord(collection)
				for j, header := range headers {
					record.Set(header, row[j])
				}

				if err := re.App.Save(record); err != nil {
					return re.JSON(http.StatusInternalServerError, map[string]string{
						"error": fmt.Sprintf("failed to save row %d: %s", i+1, err.Error()),
					})
				}
				imported++
			}

			return re.JSON(http.StatusOK, map[string]int{
				"imported": imported,
			})
		})

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
