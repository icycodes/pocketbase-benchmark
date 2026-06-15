package main

import (
	"log"
	"regexp"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/plugins/jsvm"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"
	"github.com/pocketbase/pocketbase/tools/hook"
)

// customApp wraps pocketbase.PocketBase to provide OnRecordBeforeCreateRequest
type customApp struct {
	*pocketbase.PocketBase
}

func (app *customApp) OnRecordBeforeCreateRequest(tags ...string) *hook.TaggedHook[*core.RecordRequestEvent] {
	return app.OnRecordCreateRequest(tags...)
}

func main() {
	pbApp := pocketbase.New()
	app := &customApp{PocketBase: pbApp}

	// Register JSVM and MigrateCmd to support JS migrations
	jsvm.MustRegister(app, jsvm.Config{})
	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{})

	app.OnRecordBeforeCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return apis.NewBadRequestError("Title is required.", nil)
		}

		slug := Slugify(title)
		e.Record.Set("slug", slug)

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

var slugRegex = regexp.MustCompile(`[^a-z0-9]+`)

func Slugify(s string) string {
	s = strings.ToLower(s)
	s = slugRegex.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	return s
}
