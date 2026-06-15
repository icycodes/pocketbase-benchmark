package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// 1. Create categories collection
		categories := core.NewBaseCollection("categories")
		categories.ListRule = types.Pointer("")
		categories.ViewRule = types.Pointer("")
		categories.Fields.Add(
			&core.TextField{
				Name:     "name",
				Required: true,
			},
		)
		categories.AddIndex("idx_unique_category_name", true, "`name`", "")

		if err := app.Save(categories); err != nil {
			return err
		}

		// 2. Create articles collection
		articles := core.NewBaseCollection("articles")
		articles.ListRule = types.Pointer("")
		articles.ViewRule = types.Pointer("")
		articles.Fields.Add(
			&core.TextField{
				Name:     "title",
				Required: true,
			},
			&core.TextField{
				Name:     "body",
				Required: true,
			},
			&core.RelationField{
				Name:          "category",
				Required:      true,
				MaxSelect:     1,
				CascadeDelete: true,
				CollectionId:  categories.Id,
			},
		)

		if err := app.Save(articles); err != nil {
			return err
		}

		// 3. Seed categories
		cats := []struct {
			id   string
			name string
		}{
			{"techcategory123", "Tech"},
			{"lifecategory123", "Life"},
			{"newscategory123", "News"},
		}

		for _, cat := range cats {
			rec := core.NewRecord(categories)
			rec.Set("id", cat.id)
			rec.Set("name", cat.name)
			if err := app.Save(rec); err != nil {
				return err
			}
		}

		// 4. Seed articles
		arts := []struct {
			id       string
			title    string
			body     string
			category string
		}{
			{"article1id12345", "Tech News 1", "Body of Tech News 1", "techcategory123"},
			{"article2id12345", "Tech News 2", "Body of Tech News 2", "techcategory123"},
			{"article3id12345", "Life Hacks 1", "Body of Life Hacks 1", "lifecategory123"},
			{"article4id12345", "Life Hacks 2", "Body of Life Hacks 2", "lifecategory123"},
			{"article5id12345", "World News 1", "Body of World News 1", "newscategory123"},
			{"article6id12345", "World News 2", "Body of World News 2", "newscategory123"},
		}

		for _, art := range arts {
			rec := core.NewRecord(articles)
			rec.Set("id", art.id)
			rec.Set("title", art.title)
			rec.Set("body", art.body)
			rec.Set("category", art.category)
			if err := app.Save(rec); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// Revert operation:
		// Delete articles collection
		articles, err := app.FindCollectionByNameOrId("articles")
		if err == nil {
			if err := app.Delete(articles); err != nil {
				return err
			}
		}

		// Delete categories collection
		categories, err := app.FindCollectionByNameOrId("categories")
		if err == nil {
			if err := app.Delete(categories); err != nil {
				return err
			}
		}

		return nil
	})
}
