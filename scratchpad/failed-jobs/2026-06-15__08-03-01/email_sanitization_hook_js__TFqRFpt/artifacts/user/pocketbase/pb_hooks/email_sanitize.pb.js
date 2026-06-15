// Email sanitization hook for PocketBase v0.23+
// Trims whitespace and lowercases email fields on the users collection
// before validation and persistence.
// Also sanitizes emailConfirm to ensure validation passes when present.

function sanitizeEmail(e) {
  const email = e.record.get("email");
  if (typeof email === "string") {
    const sanitized = email.trim().toLowerCase();
    e.record.set("email", sanitized);
    e.record.set("emailConfirm", sanitized);
  }
  e.next();
}

onRecordCreateRequest(sanitizeEmail, "users");

onRecordUpdateRequest(sanitizeEmail, "users");