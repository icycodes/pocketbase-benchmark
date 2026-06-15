package main

import (
	"encoding/json"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type SubscriptionResponse struct {
	Status string `json:"status"`
}

func main() {
	app := pocketbase.New()

	app.OnRecordCreateExecute("posts").BindFunc(func(e *core.RecordEvent) error {
		author := e.Record.GetString("author")

		if author == "" {
			return router.NewBadRequestError("Missing author field", nil)
		}

		resp, err := http.Get("http://localhost:8080/api/subscription?userId=" + author)
		if err != nil {
			return router.NewBadRequestError("Failed to verify subscription status", nil)
		}
		defer resp.Body.Close()

		var subResp SubscriptionResponse
		if err := json.NewDecoder(resp.Body).Decode(&subResp); err != nil {
			return router.NewBadRequestError("Failed to parse subscription response", nil)
		}

		if subResp.Status != "active" {
			return router.NewBadRequestError("User does not have an active subscription", nil)
		}

		return e.Next()
	})

	app.Start()
}