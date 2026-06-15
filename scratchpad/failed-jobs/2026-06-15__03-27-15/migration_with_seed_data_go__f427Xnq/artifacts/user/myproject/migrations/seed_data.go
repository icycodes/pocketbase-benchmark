package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/migrations"
)

func init() {
	migrations.Register(func(app core.App) error {
		// --- Create categories collection ---
		categories := core.NewBaseCollection("categories")

		categories.Fields.Add(&core.TextField{
			Name:     "name",
			Required: true,
		})

		// Add unique index on name
		categories.AddIndex("idx_categories_name_unique", true, "name", "")

		if err := app.Save(categories); err != nil {
			return err
		}

		// --- Seed categories ---
		catTech := core.NewRecord(categories)
		catTech.Set("name", "Tech")
		if err := app.Save(catTech); err != nil {
			return err
		}

		catLife := core.NewRecord(categories)
		catLife.Set("name", "Life")
		if err := app.Save(catLife); err != nil {
			return err
		}

		catNews := core.NewRecord(categories)
		catNews.Set("name", "News")
		if err := app.Save(catNews); err != nil {
			return err
		}

		// --- Create articles collection ---
		articles := core.NewBaseCollection("articles")

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
			Required:      true,
			CollectionId:  categories.Id,
			CascadeDelete: true,
			MaxSelect:     1,
		})

		if err := app.Save(articles); err != nil {
			return err
		}

		// --- Seed articles (6 total) ---
		articleData := []struct {
			title    string
			body     string
			category *core.Record
		}{
			{"Tech Breakthrough", "A major breakthrough in AI technology.", catTech},
			{"Gadget Review", "The latest smartphone reviewed in detail.", catTech},
			{"Life Hacks", "Simple tips to improve your daily routine.", catLife},
			{"Healthy Living", "How to maintain a balanced lifestyle.", catLife},
			{"World News", "Important events happening around the globe.", catNews},
			{"Local Update", "Community events and local stories.", catNews},
		}

		for _, data := range articleData {
			article := core.NewRecord(articles)
			article.Set("title", data.title)
			article.Set("body", data.body)
			article.Set("category", data.category.Id)
			if err := app.Save(article); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// Delete articles collection first (due to relation dependency)
		if articles, err := app.FindCollectionByNameOrId("articles"); err == nil {
			if err := app.Delete(articles); err != nil {
				return err
			}
		}

		// Delete categories collection
		if categories, err := app.FindCollectionByNameOrId("categories"); err == nil {
			if err := app.Delete(categories); err != nil {
				return err
			}
		}

		return nil
	})
}