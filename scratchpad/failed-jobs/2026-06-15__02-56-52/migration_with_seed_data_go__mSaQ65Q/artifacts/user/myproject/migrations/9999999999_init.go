package migrations

import (
	"fmt"

	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/migrations"
)

func init() {
	migrations.Register(func(app core.App) error {
		rule := ""

		// Create categories collection
		categories := core.NewBaseCollection("categories")
		categories.ListRule = &rule
		categories.ViewRule = &rule

		categories.Fields.Add(&core.TextField{
			Name:     "name",
			Required: true,
		})
		categories.AddIndex("idx_category_name", true, "name", "")

		if err := app.Save(categories); err != nil {
			return fmt.Errorf("failed to save categories collection: %v", err)
		}

		// Create articles collection
		articles := core.NewBaseCollection("articles")
		articles.ListRule = &rule
		articles.ViewRule = &rule

		articles.Fields.Add(&core.TextField{
			Name:     "title",
			Required: true,
		})
		articles.Fields.Add(&core.TextField{
			Name:     "body",
			Required: true,
		})
		articles.Fields.Add(&core.RelationField{
			Name:          "category",
			CollectionId:  categories.Id,
			MaxSelect:     1,
			CascadeDelete: true,
			Required:      true,
		})

		if err := app.Save(articles); err != nil {
			return fmt.Errorf("failed to save articles collection: %v", err)
		}

		// Seed categories
		catNames := []string{"Tech", "Life", "News"}
		catRecords := make(map[string]*core.Record)

		for _, name := range catNames {
			record := core.NewRecord(categories)
			record.Set("name", name)
			if err := app.Save(record); err != nil {
				return fmt.Errorf("failed to seed category %s: %v", name, err)
			}
			catRecords[name] = record
		}

		// Seed articles
		for name, catRecord := range catRecords {
			for i := 1; i <= 2; i++ {
				artRecord := core.NewRecord(articles)
				artRecord.Set("title", fmt.Sprintf("%s Article %d", name, i))
				artRecord.Set("body", fmt.Sprintf("Body of %s Article %d", name, i))
				artRecord.Set("category", catRecord.Id)
				if err := app.Save(artRecord); err != nil {
					return fmt.Errorf("failed to seed article for category %s: %v", name, err)
				}
			}
		}

		return nil
	}, func(app core.App) error {
		fmt.Println("Running down migration...")
		// Remove articles
		articles, err := app.FindCollectionByNameOrId("articles")
		if err != nil {
			fmt.Printf("Error finding articles: %v\n", err)
		} else if articles != nil {
			if err := app.Delete(articles); err != nil {
				return fmt.Errorf("failed to delete articles collection: %v", err)
			}
			fmt.Println("Deleted articles")
		}

		// Remove categories
		categories, err := app.FindCollectionByNameOrId("categories")
		if err != nil {
			fmt.Printf("Error finding categories: %v\n", err)
		} else if categories != nil {
			if err := app.Delete(categories); err != nil {
				return fmt.Errorf("failed to delete categories collection: %v", err)
			}
			fmt.Println("Deleted categories")
		}

		return nil
	})
}
