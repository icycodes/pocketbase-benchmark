PocketBase allows extending server behavior using an embedded ES5 JavaScript engine (Goja) via `pb_hooks`. A common requirement is sanitizing user input before it reaches the database to ensure data consistency.

You need to write a synchronous JSVM hook script located at `pb_hooks/users.pb.js` that intercepts record creation for the `users` collection. The hook must automatically lowercase and trim whitespace from the `email` field before the record is saved to the database.

**Constraints:**
- The script MUST be entirely synchronous; do not use `Promise` or `async/await`, as the JSVM engine does not support them.
- You MUST explicitly call `e.next()` at the end of your handler to propagate the middleware execution chain.
- Do NOT modify any files outside of the `pb_hooks/users.pb.js` script.