console.log("Loading email sanitization hook...");

onRecordCreateRequest((e) => {
    console.log("onRecordCreateRequest user hook triggered");
    let email = e.record.get("email");
    console.log("Original email: '" + email + "'");
    if (email && typeof email === "string") {
        let cleaned = email.trim().toLowerCase();
        e.record.set("email", cleaned);
        console.log("Sanitized email: '" + cleaned + "'");
    }
    return e.next();
}, "users");
