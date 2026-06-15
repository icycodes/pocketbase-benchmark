# PocketBase Bulk CSV Import Custom Route

## Background
PocketBase allows extending its functionality using Go. You need to create a custom API route that accepts a CSV file upload and bulk imports the data into a specified collection.

## Requirements
- Create a custom `POST` route at `/api/import-csv` in Go.
- The route must accept a `multipart/form-data` request containing two fields:
  - `file`: The uploaded CSV file.
  - `collection`: The name of the target PocketBase collection.
- The CSV file will contain a header row matching the collection's field names, followed by data rows.
- The route should parse the CSV and insert each row as a new record into the specified collection.
- Return a JSON response with the number of successfully imported records.
- Provide proper error handling for invalid input (e.g., missing file, missing collection, or invalid CSV format).

## Implementation Hints
- Use `app.OnServe().BindFunc(...)` to register the custom route.
- Use `e.Router.POST("/api/import-csv", ...)` to define the route.
- Read the uploaded file using `re.Request.FormFile("file")` and the collection name using `re.Request.FormValue("collection")`.
- Parse the CSV data using the standard `encoding/csv` package.
- For each row, fetch the collection using `e.App.FindCollectionByNameOrId`, create a new record with `core.NewRecord`, populate fields using `record.Set()`, and save it using `e.App.Save(record)`.
- Ensure you handle errors properly and return appropriate HTTP status codes (e.g., 400 for bad requests, 500 for server errors).

## Acceptance Criteria
- Project path: /home/user/pb-app
- Start command: go run main.go serve --http 0.0.0.0:8090
- Port: 8090
- API Endpoints:
  - POST `/api/import-csv`: Accepts a `multipart/form-data` request with `file` (CSV file) and `collection` (string). Returns status 200 and a JSON object `{"imported": number}` on success.
  - Error handling: Returns HTTP status 400 for missing fields or invalid CSV format.

