package main

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func init() {
	app := pocketbase.New()
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// create collections
		posts, err := app.FindCollectionByNameOrId("posts")
		if err != nil {
			posts = core.NewBaseCollection("posts")
			posts.Fields.Add(&core.TextField{Name: "title"})
		}
		posts.CreateRule = nil // wait, nil means blocked. "" means public.
		var publicRule string = ""
		posts.CreateRule = &publicRule
		posts.UpdateRule = &publicRule
		posts.DeleteRule = &publicRule
		posts.ViewRule = &publicRule
		posts.ListRule = &publicRule
		app.Save(posts)

		auditLog, err := app.FindCollectionByNameOrId("audit_log")
		if err != nil {
			auditLog = core.NewBaseCollection("audit_log")
			auditLog.Fields.Add(&core.TextField{Name: "actor"})
			auditLog.Fields.Add(&core.TextField{Name: "action"})
			auditLog.Fields.Add(&core.TextField{Name: "collection"})
			auditLog.Fields.Add(&core.TextField{Name: "record"})
			auditLog.Fields.Add(&core.AutodateField{Name: "at"}) // Wait, autodate field might not be right
			auditLog.Fields.Add(&core.JSONField{Name: "diff"})
		}
		auditLog.CreateRule = &publicRule
		auditLog.UpdateRule = &publicRule
		auditLog.DeleteRule = &publicRule
		auditLog.ViewRule = &publicRule
		auditLog.ListRule = &publicRule
		app.Save(auditLog)
		
		return e.Next()
	})
}
