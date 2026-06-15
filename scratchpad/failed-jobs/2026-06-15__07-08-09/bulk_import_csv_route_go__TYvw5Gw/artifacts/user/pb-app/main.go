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
		// Auto-create "projects" collection for testing purposes if it doesn't exist
		_, err := app.FindCollectionByNameOrId("projects")
		if err != nil {
			collection := core.NewBaseCollection("projects")
			collection.Fields.Add(
				&core.TextField{Name: "name"},
				&core.TextField{Name: "description"},
			)
			if err := app.Save(collection); err != nil {
				log.Println("Failed to auto-create projects collection:", err)
			} else {
				log.Println("Successfully auto-created projects collection")
			}
		}

		// Register custom CSV import route
		se.Router.POST("/api/import-csv", func(re *core.RequestEvent) error {
			collectionName := re.Request.FormValue("collection")
			if collectionName == "" {
				return re.BadRequestError("collection field is required", nil)
			}

			file, _, err := re.Request.FormFile("file")
			if err != nil {
				return re.BadRequestError("file field is required", err)
			}
			defer file.Close()

			collection, err := re.App.FindCollectionByNameOrId(collectionName)
			if err != nil {
				return re.BadRequestError("Collection not found", err)
			}

			reader := csv.NewReader(file)
			records, err := reader.ReadAll()
			if err != nil {
				return re.BadRequestError("Invalid CSV format", err)
			}

			if len(records) == 0 {
				return re.BadRequestError("CSV file is empty", nil)
			}

			headerRow := records[0]
			dataRows := records[1:]

			importedCount := 0
			err = re.App.RunInTransaction(func(txApp core.App) error {
				importedCount = 0
				for _, row := range dataRows {
					record := core.NewRecord(collection)
					for i, fieldName := range headerRow {
						if i >= len(row) {
							break
						}
						record.Set(fieldName, row[i])
					}
					if err := txApp.Save(record); err != nil {
						return err
					}
					importedCount++
				}
				return nil
			})
			if err != nil {
				return re.BadRequestError("Failed to import CSV records", err)
			}

			return re.JSON(http.StatusOK, map[string]any{
				"imported": importedCount,
			})
		})

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
