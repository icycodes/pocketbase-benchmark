package main

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
)

type pocketbaseApp struct {
	*pocketbase.PocketBase
}

func (app *pocketbaseApp) OnRecordBeforeCreateRequest(tags ...string) *hook.TaggedHook[*core.RecordRequestEvent] {
	return app.OnRecordCreateRequest(tags...)
}

func main() {
	pb := pocketbase.New()
	app := &pocketbaseApp{pb}

	app.OnRecordBeforeCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		authorID := e.Record.GetString("author")

		resp, err := http.Get("http://localhost:8080/api/subscription?userId=" + authorID)
		if err != nil {
			return e.BadRequestError("failed to verify subscription: "+err.Error(), nil)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return e.BadRequestError("failed to verify subscription: invalid response status", nil)
		}

		var result struct {
			Status string `json:"status"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return e.BadRequestError("failed to parse subscription response: "+err.Error(), nil)
		}

		if result.Status == "active" {
			return e.Next()
		}

		return e.BadRequestError("subscription is inactive", nil)
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
