Executing complex multi-step operations in PocketBase requires database transactions. However, because PocketBase's underlying SQLite database runs in WAL mode, it only allows a single concurrent writer, making it highly susceptible to `SQLITE_BUSY` deadlocks if transactions are mishandled.

You need to write a Go event hook (`OnRecordBeforeUpdateRequest` for a `wallets` collection) that executes a database transaction to atomically deduct funds from a user's wallet and simultaneously create an audit record in a `ledger` collection. 

**Constraints:**
- You MUST use the transaction-scoped app instance (e.g., `txApp`) provided in the transaction callback for all read/write operations inside the block.
- Do NOT use the global `app` or `e.App` instance inside the transaction block to prevent guaranteed deadlocks.
- Do NOT perform any slow external network requests or synchronous email dispatching within the transaction block.