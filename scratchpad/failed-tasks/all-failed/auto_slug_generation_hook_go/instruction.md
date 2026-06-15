# Auto Slug Generation Hook in Go

## Background
PocketBase allows extending its core functionality using Go event hooks. In this task, you will write a custom Go backend that embeds PocketBase and uses a hook to automatically generate a slug from a title field when a new record is created.

## Requirements
- Initialize a Go module and embed PocketBase.
- Implement an `OnRecordBeforeCreateRequest` hook for the `posts` collection.
- The hook must check if the `title` field is provided. If it is empty, the hook must return a 400 Bad Request error.
- The hook must generate a slug from the `title` field (e.g., using `core.Slugify`) and save it to the `slug` field before the record is saved to the database.
- Ensure the hook correctly propagates execution so the record is actually created.

## Implementation Hints
- Use the `github.com/pocketbase/pocketbase` package.
- Bind the hook using `app.OnRecordBeforeCreateRequest("posts").BindFunc(...)`.
- Inside the hook, retrieve the title using `e.Record.GetString("title")` and set the slug using `e.Record.Set("slug", ...)`.
- Be sure to return `e.Next()` at the end of your hook handler to continue the execution chain.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - POST `/api/collections/posts/records`: Creates a new post. When a valid `title` is provided, the API must successfully create the record and the response must contain the correctly generated `slug`.
  - POST `/api/collections/posts/records`: If `title` is missing or empty, the API must reject the request and return a 400 Bad Request error.
