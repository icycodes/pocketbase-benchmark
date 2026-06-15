# External Subscription Status Validator (Go Hook)

## Background
You are building a custom backend using PocketBase as a Go framework. You need to implement a business rule that restricts users from creating new posts unless they have an active subscription, which is managed by an external billing system.

## Requirements
- Initialize a custom PocketBase Go application.
- Implement a Go-based `OnRecordBeforeCreateRequest` hook for the `posts` collection.
- The hook must extract the `author` field (a string representing the user ID) from the record being created.
- The hook must make an HTTP GET request to an external mock REST API at `http://localhost:8080/api/subscription?userId=<author_id>`.
- If the external API responds with a JSON payload `{"status": "active"}`, the hook should allow the record creation to proceed.
- If the external API responds with any other status (e.g., `{"status": "inactive"}`), or if the request fails, the hook must reject the creation with a `BadRequestError`.

## Implementation Hints
- Create a `main.go` file and initialize PocketBase using `pocketbase.New()`.
- Use `app.OnRecordBeforeCreateRequest("posts").BindFunc(...)` to register the hook.
- Inside the hook, use `e.Record.GetString("author")` to get the author's ID.
- Use Go's standard `net/http` and `encoding/json` packages to query and parse the external API response.
- Use `e.BadRequestError(...)` to block the request if validation fails.
- Remember to call `e.Next()` to continue the hook execution chain when validation succeeds.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- Endpoints:
  - POST `/api/collections/posts/records`
    - Request Body: JSON object containing `title` and `author` (e.g., `{"title": "My Post", "author": "user123"}`).
    - Expected Behavior: If the mock API at `http://localhost:8080` returns `{"status": "active"}` for the given `author`, the record is created successfully (200 OK). If it returns `{"status": "inactive"}`, the request is rejected with a 400 Bad Request error.
