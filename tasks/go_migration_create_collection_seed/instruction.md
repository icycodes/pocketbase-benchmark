# PocketBase Go Migration: Create Collection and Seed Data

## Background
PocketBase can be extended using Go. When used as a Go framework, you can write custom migrations to manage your database schema and initial data programmatically. In this task, you will create a Go migration that creates a new collection and seeds it with initial data.

## Requirements
- Write a Go migration file (e.g., inside a `migrations` package) that will be executed when the PocketBase app starts.
- The migration must create a new collection named `configs`.
- The `configs` collection must have two fields: `key` (type: text, required: true) and `value` (type: text).
- The `configs` collection must allow public read access (List and View rules set to empty string `""`).
- The migration must insert two initial records into the `configs` collection:
  1. `key`: `site_name`, `value`: `My Site`
  2. `key`: `maintenance_mode`, `value`: `false`

## Implementation Hints
- Use `m.Register` to define the migration's `Up` and `Down` functions.
- Inside the `Up` function, create the collection using `core.NewBaseCollection("configs")` and add the required fields to `collection.Fields`.
- Set `collection.ListRule` and `collection.ViewRule` to `types.Pointer("")` to make the collection publicly readable.
- Save the collection using `app.Save(collection)`.
- After saving the collection, create new records using `core.NewRecord(collection)`, populate their fields using `record.Set("key", ...)`, and save them using `app.Save(record)`.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- Start command: `go run main.go serve --http=0.0.0.0:8090`
- Port: 8090
- API Endpoints:
  - GET `/api/collections/configs/records`: Returns status 200 and a JSON response containing the `items` array with the seeded records.

    ```json
    // Response
    {
      "page": 1,
      "perPage": 30,
      "totalItems": 2,
      "items": [
        {
          "key": "site_name",
          "value": "My Site"
        },
        {
          "key": "maintenance_mode",
          "value": "false"
        }
      ]
    }
    ```

