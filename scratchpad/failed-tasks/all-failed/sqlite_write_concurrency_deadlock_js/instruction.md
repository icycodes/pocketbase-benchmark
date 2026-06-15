# PocketBase Transactional Hook with JSVM

## Background
You have a PocketBase backend that manages `users`, `orders`, and `audit_logs` collections. You need to implement a robust order processing hook that safely updates multiple collections atomically without causing database deadlocks.

## Requirements
- Create a JSVM hook in `pb_hooks/orders.pb.js` that intercepts record creation for the `orders` collection.
- The hook must execute a database transaction to perform the following operations atomically:
  1. Retrieve the user placing the order (from the order's `user` relation field).
  2. Check if the user has enough balance in their `wallet` (a number field on the user record) to cover the order's `amount`. If not, throw a `BadRequestError`.
  3. Deduct the order's `amount` from the user's `wallet` and save the updated user record.
  4. Create a new record in the `audit_logs` collection with the fields `user` (relation), `order_amount` (number), and `action` (string set to "order_placed").
- The hook must properly handle the transaction execution context to avoid SQLite deadlocks (`SQLITE_BUSY`).
- The hook must propagate the execution chain correctly.

## Implementation Hints
- Use `onRecordBeforeCreateRequest` to intercept the order creation.
- Use `$app.runInTransaction((txApp) => { ... })` to group database operations.
- **Crucial**: Ensure you use the transaction-scoped app instance (`txApp`) for all read and write operations inside the transaction block. Using the global `$app` inside a transaction block will cause a guaranteed database deadlock in SQLite WAL mode.
- Remember to call `e.next()` at the end of your hook handler to propagate the middleware chain.
- To throw an error, use `throw new BadRequestError("Insufficient funds");`.

## Acceptance Criteria
- Project path: `/home/user/pocketbase_app`
- Start command: `./pocketbase serve --http="0.0.0.0:8090"`
- Port: 8090
- API Endpoints & Behavior:
  - POST `/api/collections/orders/records`: When a valid order is created, it returns a 200 OK. The user's `wallet` is correctly deducted, and an `audit_logs` record is created.
  - POST `/api/collections/orders/records`: When the user has insufficient funds, it returns a 400 Bad Request error, the user's wallet is unchanged, and no audit log or order is created.
  - Concurrent POST requests to `/api/collections/orders/records` must succeed without hanging the server or throwing `SQLITE_BUSY` database locked errors.

