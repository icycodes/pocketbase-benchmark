package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

// Deterministic IDs (max 15 chars) so the down-then-up cycle restores exactly
// the same data.
const (
	categoriesCollectionId = "cats00000000001"
	articlesCollectionId   = "arts00000000001"

	catTechId = "cattech00000001"
	catLifeId = "catlife00000001"
	catNewsId = "catnews00000001"

	art1Id = "art000000000001"
	art2Id = "art000000000002"
	art3Id = "art000000000003"
	art4Id = "art000000000004"
	art5Id = "art000000000005"
	art6Id = "art000000000006"
)

func init() {
	m.Register(func(app core.App) error {
		// ------------------------------------------------------------------ //
		// 1. Create the "categories" collection
		// ------------------------------------------------------------------ //
		categories := core.NewBaseCollection("categories", categoriesCollectionId)

		// name field – required + unique (enforced via index)
		categories.Fields.Add(&core.TextField{
			Name:     "name",
			Required: true,
		})

		// Unique index on name
		categories.AddIndex("idx_categories_name_unique", true, "name", "")

		// Open read access so the API test can query without auth
		listRule := ""
		viewRule := ""
		categories.ListRule = &listRule
		categories.ViewRule = &viewRule

		if err := app.Save(categories); err != nil {
			return err
		}

		// ------------------------------------------------------------------ //
		// 2. Create the "articles" collection
		// ------------------------------------------------------------------ //
		articles := core.NewBaseCollection("articles", articlesCollectionId)

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
			CollectionId:  categoriesCollectionId,
			Required:      true,
			CascadeDelete: true,
			MaxSelect:     1,
		})

		// Open read access
		articles.ListRule = &listRule
		articles.ViewRule = &viewRule

		if err := app.Save(articles); err != nil {
			return err
		}

		// ------------------------------------------------------------------ //
		// 3. Seed categories
		// ------------------------------------------------------------------ //
		seedCategories := []struct {
			id   string
			name string
		}{
			{catTechId, "Tech"},
			{catLifeId, "Life"},
			{catNewsId, "News"},
		}

		for _, sc := range seedCategories {
			rec := core.NewRecord(categories)
			rec.Id = sc.id
			rec.Set("name", sc.name)
			if err := app.Save(rec); err != nil {
				return err
			}
		}

		// ------------------------------------------------------------------ //
		// 4. Seed articles (2 per category)
		// ------------------------------------------------------------------ //
		seedArticles := []struct {
			id       string
			title    string
			body     string
			category string
		}{
			{art1Id, "Go 1.22 Released", "The Go team announced Go 1.22 with several improvements.", catTechId},
			{art2Id, "PocketBase Tips", "Ten tips for getting the most out of PocketBase.", catTechId},
			{art3Id, "Morning Routines", "How a structured morning routine can boost productivity.", catLifeId},
			{art4Id, "Healthy Eating", "Simple strategies for eating healthier every day.", catLifeId},
			{art5Id, "Election Update", "Latest updates from the upcoming general election.", catNewsId},
			{art6Id, "Market Report", "Global markets showed mixed signals this week.", catNewsId},
		}

		for _, sa := range seedArticles {
			rec := core.NewRecord(articles)
			rec.Id = sa.id
			rec.Set("title", sa.title)
			rec.Set("body", sa.body)
			rec.Set("category", sa.category)
			if err := app.Save(rec); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// ------------------------------------------------------------------ //
		// Down: delete articles first (has FK to categories), then categories.
		// Disable integrity checks so that the reference guard does not block
		// deletion when both collections are being removed in the same call.
		// ------------------------------------------------------------------ //
		articles, err := app.FindCollectionByNameOrId("articles")
		if err == nil {
			articles.IntegrityChecks(false)
			if err2 := app.Delete(articles); err2 != nil {
				return err2
			}
		}

		categories, err := app.FindCollectionByNameOrId("categories")
		if err == nil {
			categories.IntegrityChecks(false)
			if err2 := app.Delete(categories); err2 != nil {
				return err2
			}
		}

		return nil
	})
}
