// Hook: sanitize email on user record creation.
// Trims surrounding whitespace and lowercases the email value
// before the record is persisted. Only affects the "users" collection.
onRecordCreateRequest((e) => {
    if (e.collection.name === "users") {
        var email = e.record.get("email");
        if (typeof email === "string" && email.length > 0) {
            e.record.set("email", email.trim().toLowerCase());
        }
    }
    e.next();
});
