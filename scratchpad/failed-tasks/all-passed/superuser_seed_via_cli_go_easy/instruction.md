# Custom CLI Command to Seed Superuser

## Background
PocketBase allows extending its functionality using Go. You can add custom console commands to perform administrative tasks. In this task, you will create a custom CLI command to seed a superuser account programmatically.

## Requirements
- Create a custom PocketBase console command named `seed-superuser`.
- The command should accept two arguments: `email` and `password`.
- When executed, the command should create a new superuser with the provided email and password.
- If a superuser with the given email already exists, the command should update their password instead of failing (upsert behavior).

## Implementation Hints
- Use `app.RootCmd.AddCommand` with a `cobra.Command` to register your custom command.
- Use `app.FindCollectionByNameOrId(core.CollectionNameSuperusers)` to get the superusers collection.
- Create a new record using `core.NewRecord(collection)` and set the `email` and `password` fields, then save it using `app.Save(record)`.
- To handle upsert, you can try to find an existing auth record by email using `app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email)` first.

## Acceptance Criteria
- Project path: /home/user/pocketbase-app
- Command: `go run main.go seed-superuser <email> <password>`
- The command must successfully create a superuser in the database.
- The command output format doesn't have strict requirements, but it should exit with code 0 on success.
