/// <reference path="../pb_data/types.d.ts" />

/**
 * Email sanitization hook for the `users` collection.
 *
 * Trims whitespace and lowercases the email field before record creation and updates.
 * This prevents authentication issues and duplicate accounts caused by inconsistent
 * email formatting (e.g., " User@Example.com " vs "user@example.com").
 */

onRecordCreateRequest((e) => {
  const record = e.record;
  if (record && record.collection().name === "users") {
    const email = record.get("email");
    if (typeof email === "string" && email.length > 0) {
      record.set("email", email.trim().toLowerCase());
    }
  }
  e.next();
}, "users");

onRecordUpdateRequest((e) => {
  const record = e.record;
  if (record && record.collection().name === "users") {
    const email = record.get("email");
    if (typeof email === "string" && email.length > 0) {
      record.set("email", email.trim().toLowerCase());
    }
  }
  e.next();
}, "users");
