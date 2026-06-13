# PocketBase Deep Research & Dataset Plan

This document provides a highly structured technical breakdown of PocketBase, designed for creating high-quality evaluation datasets and benchmark tasks for AI coding agents.

---

## 1. Library Overview

### Description
[PocketBase](https://pocketbase.io/) is an open-source, lightweight, single-file realtime backend written in Go. Under the hood, it embeds an optimized **SQLite** database (running in WAL mode) and provides out-of-the-box support for user authentication, file storage (local or S3-compatible), a reactive Server-Sent Events (SSE) realtime subscription API, and an administrative dashboard UI.

### Ecosystem Role
PocketBase serves as a self-contained, portable backend. It can be utilized in two primary ways:
1. **Standalone Application**: Run directly as a prebuilt binary. You can extend its server-side behavior using an embedded ES5 JavaScript engine (Goja) by placing scripts in a `pb_hooks` directory.
2. **Go Framework/Library**: Imported as a standard Go module, allowing developers to embed PocketBase directly inside custom Go applications, hooks, and routers.

### Project Setup (Non-Interactive)

#### Standalone with JSVM Hooks
For a non-interactive standalone setup inside a Docker container or CLI environment:
```bash
# 1. Download and extract the latest binary (v0.39.3 in this example)
curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip
unzip pocketbase.zip -d pocketbase_app
cd pocketbase_app

# 2. Create the default directories for custom hooks and migrations
mkdir pb_hooks pb_migrations pb_public

# 3. Start the server non-interactively (binds to port 8090 by default)
./pocketbase serve --http="0.0.0.0:8090"
```

#### Go Framework Project
To initialize a custom Go executable embedding PocketBase:
```bash
# 1. Initialize Go module
mkdir my-pb-app && cd my-pb-app
go mod init my-pb-app

# 2. Install PocketBase dependency (pinning v0.23+ / v0.31+ standard)
go get github.com/pocketbase/pocketbase@v0.31.0
go mod tidy

# 3. Create a non-interactive main.go file
cat << 'EOF' > main.go
package main

import (
    "log"
    "github.com/pocketbase/pocketbase"
)

func main() {
    app := pocketbase.New()
    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
EOF

# 4. Build and start the custom backend
go build -o myapp
./myapp serve --http="0.0.0.0:8090"
```

---

## 2. Core Primitives & APIs

### Key Concepts

*   **Collections**: PocketBase schemas backed by SQLite tables. Supported types include `base` (standard data), `auth` (users/admins with built-in login/MFA), and `view` (read-only SQLite views).
    *   *Doc Link*: [PocketBase Collections Documentation](https://pocketbase.io/docs/collections/)
*   **API Rules**: SQL-like access control filters evaluated at the database level on every request.
    *   *Doc Link*: [API Rules and Filters](https://pocketbase.io/docs/api-rules-and-filters/)
*   **Event Hooks**: Interceptors triggered before or after database, authentication, mailer, or file operations.
    *   *Doc Link (Go)*: [Go Event Hooks](https://pocketbase.io/docs/go-event-hooks/)
    *   *Doc Link (JSVM)*: [JSVM Event Hooks](https://pocketbase.io/docs/js-event-hooks/)
*   **Realtime Subscriptions**: Reactive data synchronization via Server-Sent Events (SSE).
    *   *Doc Link*: [Realtime API Reference](https://pocketbase.io/docs/api-realtime/)
*   **File Storage**: Native file upload management, serving, and on-the-fly thumbnail generation.
    *   *Doc Link*: [Files REST API](https://pocketbase.io/docs/api-records/)

---

### Detailed Code Snippets

#### 1. Event Hooks (Go Framework vs. JSVM)
PocketBase v0.23+ and v0.31+ utilize a chain-of-responsibility pattern for hooks. All handlers must call the propagation method (`e.Next()` in Go, `e.next()` in JS) to proceed. Failing to do so breaks the middleware chain.

**Primary Interface (Go):**
```go
package main

import (
    "log"
    "github.com/pocketbase/pocketbase"
    "github.com/pocketbase/pocketbase/core"
)

func main() {
    app := pocketbase.New()

    // Hook triggered before creating a record in the 'posts' collection
    app.OnRecordBeforeCreateRequest("posts").BindFunc(func(e *core.RecordRequestEvent) error {
        title := e.Record.GetString("title")
        if title == "" {
            return e.BadRequestError("Title cannot be empty", nil)
        }

        // Programmatically generate slug
        e.Record.Set("slug", core.Slugify(title))

        // MUST call e.Next() to continue the hook execution chain
        return e.Next()
    })

    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
```

**Equivalent Interface (JSVM Hook inside `pb_hooks/posts.pb.js`):**
```javascript
/// <reference path="../pb_data/types.d.ts" />

onRecordBeforeCreateRequest((e) => {
    const title = e.record.get("title");
    if (!title) {
        throw new BadRequestError("Title cannot be empty");
    }

    e.record.set("slug", $String.slugify(title));

    // MUST call e.next() to propagate execution
    return e.next();
}, "posts");
```

---

#### 2. Client SDK Usage (JS vs. Dart)

**Primary Interface (JavaScript SDK):**
```javascript
import PocketBase from 'pocketbase';

const pb = new PocketBase('http://127.0.0.1:8090');

// Authenticate a user
const authData = await pb.collection('users').authWithPassword('test@example.com', 'secure_password');

// Create a new record with relations
const record = await pb.collection('posts').create({
    title: 'Hello PocketBase',
    author: pb.authStore.model.id,
    content: 'This is a test post.',
});

// Realtime subscriptions
pb.collection('posts').subscribe('*', (e) => {
    console.log('Realtime event received:', e.action, e.record);
});
```

**Equivalent Interface (Dart SDK):**
```dart
import 'package:pocketbase/pocketbase.dart';

final pb = PocketBase('http://127.0.0.1:8090');

// Authenticate a user
final authData = await pb.collection('users').authWithPassword('test@example.com', 'secure_password');

// Create a new record
final record = await pb.collection('posts').create(body: {
  'title': 'Hello PocketBase',
  'author': pb.authStore.model.id,
  'content': 'This is a test post.',
});

// Realtime subscriptions
pb.collection('posts').subscribe('*', (e) {
  print('Realtime event received: ${e.action} - ${e.record}');
});
```

---

#### 3. API Access Control Rules (SQL-Like Expressions)
Rules are configured in the collection settings (via JSON migrations or the Admin UI). They dictate user permissions based on logical expressions.

*   **Allow only the owner to update or delete a record, and prevent changing the owner field:**
    ```sql
    owner = @request.auth.id && @request.body.owner:isset = false
    ```
*   **Allow access to a "story" only if the user is the author OR has been explicitly granted edit permissions via a relational table:**
    ```sql
    @request.auth.id != "" && (
        @request.auth.id = author || 
        @request.auth.id ?= book.EditPermission_via_book.grantee
    )
    ```

---

## 3. Real-World Use Cases & Templates

### Representative Templates & Starters
*   [lucafaggianelli/pocket-saas](http://github.com/lucafaggianelli/pocket-saas): A React and Tailwind frontend template designed to launch SaaS applications using PocketBase as the back-of-house engine.
*   [dcaponi/sveltekit-pocketbase-starter](https://github.com/dcaponi/sveltekit-pocketbase-starter): A SvelteKit template demonstrating Stripe integration, full email/OAuth registration, and server-side session synchronization.

### Common Integration Patterns
*   **SSR Authentication Synchronization**: Since PocketBase is stateless and defaults to storing JWTs in browser `localStorage`, Server-Side Rendered (SSR) frameworks (Next.js, SvelteKit) require middleware to sync auth state via cookies. 
    *   *Pattern*: On incoming requests, the server-side hook reads the cookie, loads it into the SDK instance using `pb.authStore.loadFromCookie()`, performs an optional `authRefresh()`, and writes the refreshed token back to the response headers using `pb.authStore.exportToCookie()`.

---

## 4. Developer Friction Points & Edge Cases

### Friction Point 1: JSVM Concurrency and Synchronous Execution
*   **Description**: Developers trying to use `Promise`, `async/await`, or external non-blocking HTTP requests inside `pb_hooks` scripts will experience runtime syntax crashes.
*   **Symptom**: Uncaught reference errors or failures when attempting asynchronous operations (`Promise is not defined`).
*   **Underlying Cause**: PocketBase's JSVM is powered by **Goja**, a pure-Go ECMAScript 5.1 engine. It runs in a strictly synchronous execution loop. To maintain thread-safety in a multi-threaded Go environment, JSVM scripts run sequentially or under strict internal locks.
*   **Resolution**: Keep JSVM scripts synchronous. For asynchronous operations (such as multi-threaded background queues, non-blocking fetch calls, or high-performance concurrent processing), bypass JSVM and write native Go event hooks.
*   *Link*: [Extending PocketBase via JavaScript (Pockethost)](https://pockethost.io/docs/js) & [Discussion #2825](https://github.com/pocketbase/pocketbase/discussions/2825)

### Friction Point 2: SQLite Write Concurrency and Deadlocks in Transactions
*   **Description**: Attempting to execute database transactions inside custom hooks can cause the entire application server to hang or fail.
*   **Symptom**: Database deadlock or locking exceptions: `database is locked (SQLITE_BUSY)`.
*   **Underlying Cause**: SQLite's WAL mode allows multiple concurrent readers but only a **single concurrent writer**. If a developer opens a transaction block and performs writes using the global `$app` (JS) or `app` (Go) instance instead of the transaction-scoped `txApp` context, a deadlock is guaranteed.
*   **Resolution**: Developers must **always** use the transaction-scoped app instance (e.g., `txApp`) passed to the transaction callback. Never execute slow external network requests or send emails inside the transaction block, as this holds the SQLite write lock open too long.
*   *Link*: [Extend with JavaScript - Record operations](https://pocketbase.io/docs/js-records/)

### Friction Point 3: Breaking Hook API Signature in v0.23+
*   **Description**: Upgrading older PocketBase instances (v0.22.x or earlier) to v0.23.0+ silently breaks or crashes existing Go hooks, JSVM scripts, and API rules.
*   **Symptom**: Custom hooks fail to fire, or operations are blocked entirely. Compile-time errors like `OnRecordBeforeCreateRequest().Add is undefined` in Go, or runtime errors regarding missing hook middleware propagation.
*   **Underlying Cause**: PocketBase v0.23.0 introduced a major API overhaul. Hook registration was changed from `.Add()` to `.BindFunc()`. Crucially, hook handlers must now return `e.Next()` (or `e.next()` in JS) to propagate execution. If omitted, the operation is blocked. Additionally, `@request.data.*` was renamed to `@request.body.*` in API rules.
*   **Resolution**: Rewrite hooks to use `.BindFunc()`, ensure `e.Next()` / `e.next()` is called at the end of every hook handler, and update collection API rules to target `@request.body.*`.
*   *Link*: [Upgrade to v0.23.0 (Go) Guide](https://pocketbase.io/v023upgrade/go/) & [Discussion #6371](https://github.com/pocketbase/pocketbase/discussions/6371)

### Friction Point 4: S3-Compatible Storage Proxying and Large File Upload Limits
*   **Description**: When S3 storage is enabled, large file uploads fail or server memory spikes, and file URLs do not point directly to the S3 bucket.
*   **Symptom**: High memory usage/crashes during large file uploads (>20MB) and latency on file downloads.
*   **Underlying Cause**: PocketBase proxies file requests through its own `/api/files/*` endpoint to enforce Collection `ViewRule` permissions and generate lazy thumbnails. For uploads, PocketBase buffers the request body on the server before sending it to S3, which can cause memory exhaustion on large files.
*   **Resolution**: For public files, construct direct S3 URLs (`https://bucket.s3.amazonaws.com/...`) on the client side to bypass PocketBase. For large files (>20MB), implement direct-to-bucket uploads via AWS presigned URLs.
*   *Link*: [Discussion #4447](https://github.com/pocketbase/pocketbase/discussions/4447) & [Discussion #2520](https://github.com/pocketbase/pocketbase/discussions/2520)

---

## 5. Evaluation Ideas

### Simple Difficulty
1.  **Strict Email Sanitization Hook**: Write a JSVM hook (`pb_hooks`) that intercept record creation on the `users` collection to automatically lowercase and trim whitespace from the email field before saving.
2.  **Basic Public Read/Private Write Collection**: Configure a "contacts" collection where anyone (including guests) can read entries, but only authenticated users can create, update, or delete them.

### Medium Difficulty
1.  **Relational Access Control Rule**: Configure an API rule on a "tasks" collection so that users can only list and view tasks if they are assigned to the parent "project" via a relational field.
2.  **External Subscription Status Validator**: Implement a Go-based `OnRecordBeforeCreateRequest` hook that queries an external mock REST API to verify a user's subscription status before allowing them to create a new record.
3.  **SvelteKit Auth Cookie Sync Middleware**: Implement a `hooks.server.js` middleware that correctly reads PocketBase auth state from client cookies, verifies it on the server, and returns the refreshed token back in the response headers.

### Complex Difficulty
1.  **Transactional Ledger Hook**: Write a Go event hook that executes a database transaction to atomically deduct funds from a user's wallet record, create an audit ledger record, and handle potential SQLite deadlocks or rollback scenarios correctly.
2.  **Advanced Multi-Tenant Organization Permissions**: Design a set of PocketBase API rules for an "organizations" and "documents" schema where users can only view documents if they are members of the organization, and can only edit them if they have an "editor" role inside that specific organization.

---

## 6. Sources

1.  [PocketBase Official Documentation](https://pocketbase.io/docs/): Core documentation covering setup, architecture, and deployment.
2.  [PocketBase Go Packages Reference](https://pkg.go.dev/github.com/pocketbase/pocketbase): Official Go API reference documentation for core interfaces.
3.  [PocketBase GitHub Repository](https://github.com/pocketbase/pocketbase): Source code, release notes, and issue tracker.
4.  [PocketBase JavaScript SDK GitHub](https://github.com/pocketbase/js-sdk): Client library usage, type definition, and source code.
5.  [PocketBase Dart SDK GitHub](https://github.com/pocketbase/dart-sdk): Official Dart client SDK implementation details.
6.  [PocketBase Discussion #3201](https://github.com/pocketbase/pocketbase/discussions/3201): Deep dive into cookie-based authentication with Next.js Server Actions.
7.  [PocketBase Discussion #2939](https://github.com/pocketbase/pocketbase/discussions/2939): Next.js middleware and cookie synchronization patterns.
8.  [PocketBase Discussion #2825](https://github.com/pocketbase/pocketbase/discussions/2825): Performance, concurrency, and architecture of the Goja JS VM interpreter.
9.  [PocketBase Discussion #6371](https://github.com/pocketbase/pocketbase/discussions/6371): Troubleshooting guide for broken hooks post-v0.23 upgrade.
10. [PocketBase Discussion #4447](https://github.com/pocketbase/pocketbase/discussions/4447): S3 proxy behavior and custom public S3 URL construction.
11. [PocketBase Discussion #2520](https://github.com/pocketbase/pocketbase/discussions/2520): Best practices for setting up separate buckets for backups and file uploads.
12. [Pockethost JSVM Docs](https://pockethost.io/docs/js): Community documentation covering JSVM limitations, synchronous execution, and environment variables.

---

## Notes for Generating Tasks

- Ensure all tasks target the latest version introduced in this document (v0.31.0).
- When generating pytest code, double-check the code and documentation to ensure that test cases use the correct and existing API for the specified version.

