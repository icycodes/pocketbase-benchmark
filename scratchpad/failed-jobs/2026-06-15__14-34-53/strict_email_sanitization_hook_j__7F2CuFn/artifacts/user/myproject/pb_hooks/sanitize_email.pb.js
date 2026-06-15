onRecordBeforeCreateRequest((e) => {
    const email = e.record.get("email");
    if (typeof email === "string" && email.length > 0) {
        e.record.set("email", email.trim().toLowerCase());
    }
}, "users");
