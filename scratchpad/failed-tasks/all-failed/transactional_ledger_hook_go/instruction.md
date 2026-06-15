# Transactional Ledger Route (Go)

## Background
PocketBase uses SQLite in WAL mode, which allows multiple concurrent readers but only a single concurrent writer. We need to implement a financial transaction endpoint that deducts funds from a user's wallet and creates an audit ledger record atomically, without causing SQLite deadlocks.

## Requirements
- Create a Go-based PocketBase application.
- You assume the database already has two collections:
  - `wallets` with a `balance` field (number).
  - `ledger` with `wallet_id` (relation to wallets) and `amount` (number) fields.
- Implement a custom API route `POST /api/withdraw` that accepts a JSON payload: `{"wallet_id": "<id>", "amount": <number>}`.
- The route must execute a database transaction.
- Inside the transaction, fetch the wallet record. If the `balance` is less than the `amount`, return a 400 Bad Request error.
- Deduct the `amount` from the wallet's `balance` and save the updated wallet record.
- Create a new `ledger` record linking to the `wallet_id` and storing the deducted `amount`.
- **Crucial**: Both the wallet update and the ledger creation must be performed using the transaction-scoped app instance. Using the global app instance for writes inside a transaction block will cause a guaranteed SQLite deadlock.

## Implementation Hints
- Initialize a standard PocketBase Go app.
- Register a custom route using `app.OnServe().BindFunc(...)` or `app.BindFunc(...)` depending on the PocketBase v0.31+ API.
- Use `app.RunInTransaction(func(txApp core.App) error { ... })` to wrap your operations.
- Inside the transaction, use `txApp.FindRecordById("wallets", walletId)` to get the wallet, `txApp.Save(wallet)` to update it, and `core.NewRecord(txApp.Collection("ledger"))` / `txApp.Save(ledger)` to create the ledger entry.
- Return appropriate JSON responses for success and errors using the echo context (or standard http depending on the router).

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - `POST /api/withdraw`: 
    - Accepts JSON: `{"wallet_id": "<id>", "amount": <number>}`
    - Returns status 200 on successful withdrawal.
    - Returns status 400 if the wallet has insufficient funds.
    - Must atomically update the wallet balance and create a ledger record.
    - Must not deadlock (which happens if the global app instance is used for writes inside the transaction).

