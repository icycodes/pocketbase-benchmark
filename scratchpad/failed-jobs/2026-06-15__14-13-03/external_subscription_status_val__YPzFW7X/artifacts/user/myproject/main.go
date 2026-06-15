package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

// subscriptionResponse maps the JSON body returned by the external billing API.
type subscriptionResponse struct {
	Status string `json:"status"`
}

// checkSubscription queries the external billing API and returns true only when
// the user identified by userID holds an active subscription.
func checkSubscription(userID string) (bool, error) {
	url := fmt.Sprintf("http://localhost:8080/api/subscription?userId=%s", userID)

	resp, err := http.Get(url) //nolint:noctx // simple internal hook, no deadline needed
	if err != nil {
		return false, fmt.Errorf("subscription API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("subscription API returned status %d", resp.StatusCode)
	}

	var payload subscriptionResponse
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return false, fmt.Errorf("failed to decode subscription response: %w", err)
	}

	return payload.Status == "active", nil
}

func main() {
	app := pocketbase.New()

	// Hook: validate subscription before a post record is created.
	// OnRecordCreateRequest fires before the record is persisted (PocketBase v0.39+).
	app.OnRecordCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
		authorID := e.Record.GetString("author")

		if authorID == "" {
			return e.BadRequestError("author field is required", nil)
		}

		active, err := checkSubscription(authorID)
		if err != nil {
			// Treat any connectivity / parsing failure as a rejection so that
			// an outage in the billing service cannot be exploited to bypass the check.
			log.Printf("[subscription hook] error checking subscription for user %q: %v", authorID, err)
			return e.BadRequestError("could not verify subscription status", err)
		}

		if !active {
			return e.BadRequestError("user does not have an active subscription", nil)
		}

		// Subscription is active – continue the hook chain.
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
