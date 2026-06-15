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
		se.Router.POST("/api/import-csv", func(e *core.RequestEvent) error {
			collectionName := e.Request.FormValue("collection")
			if collectionName == "" {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "collection is required"})
			}

			file, _, err := e.Request.FormFile("file")
			if err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "file is required"})
			}
			defer file.Close()

			csvReader := csv.NewReader(file)
			records, err := csvReader.ReadAll()
			if err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "invalid csv format"})
			}

			if len(records) < 1 {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "csv must contain at least a header"})
			}

			headers := records[0]
			dataRows := records[1:]

			collection, err := e.App.FindCollectionByNameOrId(collectionName)
			if err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("collection %s not found", collectionName)})
			}

			imported := 0
			for _, row := range dataRows {
				if len(row) != len(headers) {
					return e.JSON(http.StatusBadRequest, map[string]string{"error": "invalid csv format"})
				}

				record := core.NewRecord(collection)
				for i, header := range headers {
					record.Set(header, row[i])
				}

				if err := e.App.Save(record); err != nil {
					return e.JSON(http.StatusInternalServerError, map[string]string{"error": fmt.Sprintf("failed to save record: %v", err)})
				}
				imported++
			}

			return e.JSON(http.StatusOK, map[string]int{"imported": imported})
		})
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
