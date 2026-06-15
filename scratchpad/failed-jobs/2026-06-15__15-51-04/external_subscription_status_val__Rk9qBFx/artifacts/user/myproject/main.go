package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		authorID := e.Record.GetString("author")
		if authorID == "" {
			return e.BadRequestError("missing author field", nil)
		}

		url := fmt.Sprintf("http://localhost:8080/api/subscription?userId=%s", authorID)

		resp, err := http.Get(url)
		if err != nil {
			return e.BadRequestError("failed to validate subscription status", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return e.BadRequestError("subscription validation service returned an error", nil)
		}

		var result struct {
			Status string `json:"status"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return e.BadRequestError("failed to parse subscription response", err)
		}

		if result.Status != "active" {
			return e.BadRequestError("user does not have an active subscription", nil)
		}

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
