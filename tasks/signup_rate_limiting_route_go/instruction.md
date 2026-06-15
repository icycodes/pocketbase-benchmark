# Rate-Limited Custom Signup Route in Go

## Background
Implement a custom user signup route in a PocketBase Go application and protect it against abuse by adding a rate limit.

## Requirements
- You have a basic PocketBase Go project at `/workspace/pb`.
- Add a custom route `POST /api/custom_signup`.
- The route should accept a JSON payload with `email`, `password`, and `passwordConfirm`, and create a new record in the `users` collection.
- The route must be rate-limited to allow a maximum of 5 requests per 1 minute per IP address.
- The 6th request from the same IP within the 1-minute window must return a `429 Too Many Requests` status code.

## Implementation Hints
- You can use PocketBase's built-in `apis.RateLimit()` middleware by configuring the app settings, or implement a custom rate limiting middleware using standard Go libraries (e.g., `golang.org/x/time/rate`).
- To create a user, you'll need to interact with the PocketBase `users` collection programmatically using `core.NewRecord()` and `app.Save()`.
- Ensure the application is started using `go run main.go serve --http=0.0.0.0:8090`.

## Acceptance Criteria
- Project path: /workspace/pb
- Start command: go run main.go serve --http=0.0.0.0:8090
- Port: 8090
- API Endpoints:
  - POST `/api/custom_signup`: Accepts a JSON body and creates a user.

    ```json
    // Request
    {
      "email": "string",
      "password": "string",
      "passwordConfirm": "string"
    }
    ```
    ```json
    // Response (Success)
    // Status 200 OK or 201 Created
    {
      // can be any success indicator or the created user object
    }
    ```
    ```json
    // Response (Rate Limited)
    // Status 429 Too Many Requests
    ```

