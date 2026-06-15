package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// ── Create categories collection ──
		categories := core.NewBaseCollection("categories")
		categories.ListRule = types.Pointer("")
		categories.ViewRule = types.Pointer("")
		categories.Fields.Add(
			&core.TextField{
				Name:     "name",
				Required: true,
				Max:      100,
			},
		)
		// make name unique
		categories.AddIndex("idx_categories_name", true, "name", "")

		if err := app.Save(categories); err != nil {
			return err
		}

		// ── Create articles collection ──
		articles := core.NewBaseCollection("articles")
		articles.ListRule = types.Pointer("")
		articles.ViewRule = types.Pointer("")
		articles.Fields.Add(
			&core.TextField{
				Name:     "title",
				Required: true,
				Max:      255,
			},
			&core.TextField{
				Name:     "body",
				Required: true,
				Max:      10000,
			},
			&core.RelationField{
				Name:          "category",
				Required:      true,
				CollectionId:  categories.Id,
				CascadeDelete: true,
			},
		)

		if err := app.Save(articles); err != nil {
			return err
		}

		// ── Seed categories ──
		categoryNames := []string{"Tech", "Life", "News"}
		categoryRecords := make(map[string]*core.Record, 3)

		for _, name := range categoryNames {
			rec := core.NewRecord(categories)
			rec.Set("name", name)
			if err := app.Save(rec); err != nil {
				return err
			}
			categoryRecords[name] = rec
		}

		// ── Seed articles (6 total, 2 per category) ──
		type articleSeed struct {
			title    string
			body     string
			category string
		}

		seeds := []articleSeed{
			{"Getting Started with Go Generics", "Go generics allow you to write flexible, type-safe code. This article explores the basics of type parameters, constraints, and how to use them effectively in your projects.", "Tech"},
			{"Understanding Docker Compose", "Docker Compose simplifies multi-container application management. Learn how to define services, networks, and volumes in a single YAML file for reproducible deployments.", "Tech"},
			{"Morning Routines for Productivity", "Starting your day with intention can transform your productivity. Explore proven morning routines that successful people use to stay focused and energized.", "Life"},
			{"Minimalist Living Guide", "Minimalism is about focusing on what truly matters. This guide covers practical steps to declutter your space, reduce stress, and live more intentionally.", "Life"},
			{"Global Climate Summit Highlights", "World leaders gathered to discuss urgent climate action. Key takeaways include new emissions targets, green technology investments, and international cooperation frameworks.", "News"},
			{"Tech Industry Layoffs Analysis", "Recent layoffs across major tech companies signal a shift in the industry. We analyze the underlying causes, market trends, and what it means for the future of work.", "News"},
		}

		for _, s := range seeds {
			rec := core.NewRecord(articles)
			rec.Set("title", s.title)
			rec.Set("body", s.body)
			rec.Set("category", categoryRecords[s.category].Id)
			if err := app.Save(rec); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// ── Down: delete articles collection ──
		articles, err := app.FindCollectionByNameOrId("articles")
		if err == nil {
			// delete all article records first
			articleRecords, err := app.FindAllRecords("articles")
			if err != nil {
				return err
			}
			for _, rec := range articleRecords {
				if err := app.Delete(rec); err != nil {
					return err
				}
			}
			// delete the collection
			if err := app.Delete(articles); err != nil {
				return err
			}
		}

		// ── Down: delete categories collection ──
		categories, err := app.FindCollectionByNameOrId("categories")
		if err == nil {
			// delete all category records first
			categoryRecords, err := app.FindAllRecords("categories")
			if err != nil {
				return err
			}
			for _, rec := range categoryRecords {
				if err := app.Delete(rec); err != nil {
					return err
				}
			}
			// delete the collection
			if err := app.Delete(categories); err != nil {
				return err
			}
		}

		return nil
	})
}
