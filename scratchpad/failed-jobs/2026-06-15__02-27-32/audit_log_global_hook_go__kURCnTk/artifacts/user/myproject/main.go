package main

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
	"github.com/pocketbase/pocketbase/tools/types"
)

func main() {
	app := pocketbase.New()

	// Ensure required collections exist after bootstrap.
	app.OnBootstrap().Bind(&hook.Handler[*core.BootstrapEvent]{
		Func: func(e *core.BootstrapEvent) error {
			if err := e.Next(); err != nil {
				return err
			}
			if err := ensureCollections(e.App); err != nil {
				return fmt.Errorf("ensure collections: %w", err)
			}
			return nil
		},
		Priority: 10,
	})

	// ----------------------------------------------------------------
	// Audit hook: CREATE
	// ----------------------------------------------------------------
	app.OnRecordCreateRequest().Bind(&hook.Handler[*core.RecordRequestEvent]{
		Func: func(e *core.RecordRequestEvent) error {
			// Call next first so the record is actually saved.
			if err := e.Next(); err != nil {
				return err
			}
			// Skip system collections and audit_log itself.
			colName := e.Record.Collection().Name
			if shouldSkip(colName) {
				return nil
			}
			actor := actorFromRequest(e.RequestEvent)
			return writeAudit(e.App, actor, "create", colName, e.Record.Id, nil)
		},
		Priority: 999, // run last so e.Next() completes the full save pipeline
	})

	// ----------------------------------------------------------------
	// Audit hook: UPDATE
	// ----------------------------------------------------------------
	app.OnRecordUpdateRequest().Bind(&hook.Handler[*core.RecordRequestEvent]{
		Func: func(e *core.RecordRequestEvent) error {
			// Snapshot original (pre-update) field values BEFORE calling Next.
			// e.Record was fetched from DB so e.Record.Original().FieldsData()
			// holds the current DB state.
			oldData := e.Record.Original().FieldsData()

			// Execute the actual update.
			if err := e.Next(); err != nil {
				return err
			}

			// Skip system collections and audit_log itself.
			colName := e.Record.Collection().Name
			if shouldSkip(colName) {
				return nil
			}

			// Build diff: only fields whose value changed.
			newData := e.Record.FieldsData()
			diff := buildDiff(oldData, newData)

			actor := actorFromRequest(e.RequestEvent)
			return writeAudit(e.App, actor, "update", colName, e.Record.Id, diff)
		},
		Priority: 999,
	})

	// ----------------------------------------------------------------
	// Audit hook: DELETE
	// ----------------------------------------------------------------
	app.OnRecordDeleteRequest().Bind(&hook.Handler[*core.RecordRequestEvent]{
		Func: func(e *core.RecordRequestEvent) error {
			// Capture record info before deletion.
			colName := e.Record.Collection().Name
			recordId := e.Record.Id
			actor := actorFromRequest(e.RequestEvent)

			// Execute the actual delete.
			if err := e.Next(); err != nil {
				return err
			}

			// Skip system collections and audit_log itself.
			if shouldSkip(colName) {
				return nil
			}

			return writeAudit(e.App, actor, "delete", colName, recordId, nil)
		},
		Priority: 999,
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

// shouldSkip returns true for the audit_log collection itself and for
// PocketBase system collections (names starting with "_").
func shouldSkip(collectionName string) bool {
	return collectionName == "audit_log" || strings.HasPrefix(collectionName, "_")
}

// actorFromRequest returns the authenticated user ID from the request, or
// "anon" when there is no authenticated user.
func actorFromRequest(e *core.RequestEvent) string {
	if e != nil && e.Auth != nil {
		return e.Auth.Id
	}
	return "anon"
}

// fieldValueToJSON converts a record field value to a JSON-serialisable form.
// This ensures consistent comparisons and storage even for special types
// like types.DateTime, types.JSONRaw, etc.
func fieldValueToJSON(v any) any {
	if v == nil {
		return nil
	}
	// Marshal and unmarshal to get a plain JSON-compatible value.
	b, err := json.Marshal(v)
	if err != nil {
		return fmt.Sprintf("%v", v)
	}
	var out any
	if err := json.Unmarshal(b, &out); err != nil {
		return fmt.Sprintf("%v", v)
	}
	return out
}

// buildDiff compares old and new field data and returns only the fields that
// changed, in the shape {"<field>":{"old":<old_value>,"new":<new_value>}}.
func buildDiff(oldData, newData map[string]any) map[string]any {
	diff := make(map[string]any)
	for key, newVal := range newData {
		oldVal := oldData[key]
		oldJSON := fieldValueToJSON(oldVal)
		newJSON := fieldValueToJSON(newVal)

		// Compare via JSON representation for type-safe equality.
		oldBytes, _ := json.Marshal(oldJSON)
		newBytes, _ := json.Marshal(newJSON)
		if string(oldBytes) != string(newBytes) {
			diff[key] = map[string]any{
				"old": oldJSON,
				"new": newJSON,
			}
		}
	}
	return diff
}

// writeAudit inserts a single row into the audit_log collection.
// diff may be nil for create/delete (stored as empty JSON object).
func writeAudit(app core.App, actor, action, collection, recordId string, diff map[string]any) error {
	auditCol, err := app.FindCachedCollectionByNameOrId("audit_log")
	if err != nil {
		return fmt.Errorf("audit_log collection not found: %w", err)
	}

	record := core.NewRecord(auditCol)
	record.Set("actor", actor)
	record.Set("action", action)
	record.Set("collection", collection)
	record.Set("record", recordId)
	record.Set("at", types.NowDateTime())

	if diff == nil {
		diff = map[string]any{}
	}
	diffBytes, err := json.Marshal(diff)
	if err != nil {
		return fmt.Errorf("marshal diff: %w", err)
	}
	record.Set("diff", string(diffBytes))

	// Use SaveNoValidate to avoid triggering validation hooks that might cause
	// recursion or unwanted side effects; audit rows are internal.
	return app.SaveNoValidate(record)
}

// ensureCollections creates the `posts` and `audit_log` collections if they
// do not already exist.
func ensureCollections(app core.App) error {
	if err := ensurePostsCollection(app); err != nil {
		return err
	}
	return ensureAuditLogCollection(app)
}

func ensurePostsCollection(app core.App) error {
	_, err := app.FindCachedCollectionByNameOrId("posts")
	if err == nil {
		return nil // already exists
	}

	col := core.NewBaseCollection("posts")

	col.Fields.Add(&core.TextField{
		Name:     "title",
		Required: false,
	})

	// Open API access rules (empty string = everyone allowed).
	createRule := ""
	viewRule := ""
	updateRule := ""
	deleteRule := ""
	col.CreateRule = &createRule
	col.ViewRule = &viewRule
	col.UpdateRule = &updateRule
	col.DeleteRule = &deleteRule
	col.ListRule = &viewRule

	return app.Save(col)
}

func ensureAuditLogCollection(app core.App) error {
	_, err := app.FindCachedCollectionByNameOrId("audit_log")
	if err == nil {
		return nil // already exists
	}

	col := core.NewBaseCollection("audit_log")

	col.Fields.Add(
		&core.TextField{Name: "actor"},
		&core.TextField{Name: "action"},
		&core.TextField{Name: "collection"},
		&core.TextField{Name: "record"},
		&core.DateField{Name: "at"},
		&core.JSONField{Name: "diff"},
	)

	// Keep audit_log locked down – no public API access.
	col.CreateRule = nil
	col.ViewRule = nil
	col.UpdateRule = nil
	col.DeleteRule = nil
	col.ListRule = nil

	return app.Save(col)
}
