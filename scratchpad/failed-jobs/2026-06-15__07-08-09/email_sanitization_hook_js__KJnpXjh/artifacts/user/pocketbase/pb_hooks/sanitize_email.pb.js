onRecordCreateRequest((e) => {
    const email = e.record.get("email");
    if (typeof email === "string") {
        e.record.set("email", email.trim().toLowerCase());
    }
    e.next();
}, "users");

onRecordUpdateRequest((e) => {
    const email = e.record.get("email");
    if (typeof email === "string") {
        e.record.set("email", email.trim().toLowerCase());
    }
    e.next();
}, "users");
