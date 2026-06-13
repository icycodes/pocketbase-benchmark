PocketBase v0.23.0 introduced a major API overhaul that silently breaks existing Go event hooks. Hook registration was changed, and middleware handlers are now required to actively propagate execution or the request will halt.

You need to refactor a legacy PocketBase Go hook (which currently uses `app.OnRecordBeforeCreateRequest("posts").Add(...)`) into the v0.23+ standard in a `main.go` file. The refactored hook must validate that a post's title is not empty, generate a slug, and properly continue the chain of responsibility.

**Constraints:**
- You MUST update the event registration method to use `.BindFunc()`.
- You MUST return `e.Next()` at the end of the handler to ensure the operation is not blocked.
- Any references to the legacy `@request.data` must be mentally migrated or avoided, strictly using the new `core.RecordRequestEvent` signature.