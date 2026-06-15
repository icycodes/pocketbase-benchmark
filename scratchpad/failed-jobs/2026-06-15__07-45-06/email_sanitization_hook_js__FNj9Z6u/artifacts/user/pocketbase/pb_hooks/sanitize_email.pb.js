onRecordCreateRequest((e) => {
    let email = e.record.get("email");
    if (email) {
        e.record.set("email", email.trim().toLowerCase());
    }
    e.next();
}, "users");

onRecordUpdateRequest((e) => {
    let email = e.record.get("email");
    if (email) {
        e.record.set("email", email.trim().toLowerCase());
    }
    e.next();
}, "users");
