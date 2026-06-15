package main

import (
    "log"
    "regexp"
    "strings"

    "github.com/pocketbase/pocketbase"
    "github.com/pocketbase/pocketbase/apis"
    "github.com/pocketbase/pocketbase/core"
    "github.com/pocketbase/pocketbase/tools/hook"
)

type MyApp struct {
    *pocketbase.PocketBase
}

func (app *MyApp) OnRecordBeforeCreateRequest(tags ...string) *hook.TaggedHook[*core.RecordEvent] {
    return app.OnRecordCreateExecute(tags...)
}

func slugify(title string) string {
    s := strings.ToLower(title)
    s = regexp.MustCompile(`[^a-z0-9]+`).ReplaceAllString(s, "-")
    return strings.Trim(s, "-")
}

func main() {
    baseApp := pocketbase.New()
    app := &MyApp{baseApp}

    app.OnRecordBeforeCreateRequest("posts").BindFunc(func(e *core.RecordEvent) error {
        title := e.Record.GetString("title")
        if title == "" {
            return apis.NewBadRequestError("Title is required", nil)
        }
        
        slug := slugify(title)
        e.Record.Set("slug", slug)
        
        return e.Next()
    })

    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
