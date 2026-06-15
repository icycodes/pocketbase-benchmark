package main

import (
	"encoding/csv"
	"io"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.POST("/api/import-csv", func(re *core.RequestEvent) error {
			collectionName := re.Request.FormValue("collection")
			if collectionName == "" {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "missing 'collection' field",
				})
			}

			file, _, err := re.Request.FormFile("file")
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "missing or invalid 'file' field",
				})
			}
			defer file.Close()

			reader := csv.NewReader(file)
			headers, err := reader.Read()
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "failed to read CSV header row",
				})
			}

			collection, err := e.App.FindCollectionByNameOrId(collectionName)
			if err != nil {
				return re.JSON(http.StatusBadRequest, map[string]string{
					"error": "collection not found: " + collectionName,
				})
			}

			imported := 0
			for {
				row, err := reader.Read()
				if err == io.EOF {
					break
				}
				if err != nil {
					return re.JSON(http.StatusBadRequest, map[string]string{
						"error": "invalid CSV format",
					})
				}

				record := core.NewRecord(collection)
				for i, header := range headers {
					if i < len(row) {
						record.Set(header, row[i])
					}
				}

				if err := e.App.Save(record); err != nil {
					return re.JSON(http.StatusInternalServerError, map[string]string{
						"error": "failed to save record: " + err.Error(),
					})
				}
				imported++
			}

			return re.JSON(http.StatusOK, map[string]int{
				"imported": imported,
			})
		})

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
