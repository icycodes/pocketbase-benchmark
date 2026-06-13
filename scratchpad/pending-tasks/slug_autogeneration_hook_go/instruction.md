# PocketBase Go Event Hook: Auto-Generate Article Slugs

## Background
You are extending a PocketBase v0.31.0 backend that powers a small CMS. The Go application already provisions a base `articles` collection via a Go migration. Your job is to add a **server-side Go event hook** that validates and enriches incoming article creation requests so that every article ends up with a non-empty title and a URL-friendly `slug` auto-derived from the title.

The project already includes the PocketBase Go dependency, a registered migration that creates the `articles` collection, and a minimal `main.go`. You will need to wire the hook on the correct lifecycle event and make sure it cooperates with the v0.23+ chained-handler API (`BindFunc` + `e.Next()`).

## Requirements
- Register a Go event hook on **record creation requests** for the `articles` collection (i.e. wrap behavior around the public REST `POST /api/collections/articles/records` endpoint, not internal `app.Save` calls).
- Reject the request with an HTTP `400 Bad Request` whenever the submitted `title` field is missing, empty, or only whitespace. The hook MUST NOT persist a record in those cases.
- For valid titles, populate the `slug` field with a URL-friendly representation derived from the trimmed title with the following rules:
  - Lowercase ASCII letters.
  - ASCII alphanumeric characters (`a-z`, `0-9`) are preserved.
  - Any sequence of one or more non-alphanumeric characters (spaces, punctuation, symbols, underscores, etc.) collapses into a single `-` separator.
  - No leading or trailing `-` in the final slug.
- The hook MUST overwrite any client-supplied `slug` value with the auto-generated one (the slug is always derived from the title).
- Continue to propagate the request chain so that PocketBase actually saves the record. Forgetting to call `e.Next()` will block all article creation and is a known v0.23+ pitfall.
- Keep the `main.go` runnable as a standalone PocketBase backend (`./articles-app serve --http=0.0.0.0:8090`). Do not remove the existing migration registration or change the `articles` schema.

## Implementation Hints
- The PocketBase v0.31 Go API uses chained hooks. Register your handler with `app.OnRecordCreateRequest("articles").BindFunc(func(e *core.RecordRequestEvent) error { ... })` and return `e.Next()` at the end of the success path.
- Use the `*core.RecordRequestEvent` to read and mutate the in-flight record (`e.Record.GetString`, `e.Record.Set`). Use `e.BadRequestError(message, nil)` to short-circuit with a 400 response.
- PocketBase does not ship a guaranteed public `Slugify` helper in v0.31, so implement the transformation yourself in pure Go (a single pass over the runes is enough).
- The existing `migrations` package is already imported and the collection has fields `title` (text, required) and `slug` (text). All API rules are open (`""`) so unauthenticated clients can create records during testing.
- Build with `go build -o articles-app .` from the project directory.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./articles-app serve --http=0.0.0.0:8090
- Port: 8090
- The PocketBase admin/REST server must be reachable on port 8090 after start.
- API Endpoints exercised by verification (provided by PocketBase, gated by your hook):
  - POST `/api/collections/articles/records`: Accepts a JSON body with `title` (string, required) and optionally `content` (string). Any submitted `slug` MUST be ignored.
    ```json
    // Request
    {
      "title": string,
      "content": string
    }
    ```
    - On success returns HTTP 200 (PocketBase default) with a JSON object whose `title` matches the input and whose `slug` follows the slug rules described in Requirements.
    - On invalid title (missing, empty, or whitespace-only) returns HTTP 400 and does NOT create a record.
  - GET `/api/collections/articles/records`: Standard PocketBase list endpoint. Used only to confirm that rejected requests did not persist any row.
- Slug rules (these are the externally observable acceptance rules, not implementation steps):
  - Always derived from the trimmed `title`.
  - Lowercase ASCII letters and digits are preserved.
  - Runs of non-alphanumeric characters collapse to exactly one `-`.
  - No leading or trailing `-`.
  - Client-supplied `slug` values in the request body are overwritten.

