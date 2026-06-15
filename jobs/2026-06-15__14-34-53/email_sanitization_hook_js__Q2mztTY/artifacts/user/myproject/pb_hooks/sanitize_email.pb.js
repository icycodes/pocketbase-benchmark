onRecordCreateRequest((e) => {
    if (e.collection.name === "users") {
        var email = e.record.get("email");
        if (email) {
            e.record.set("email", String(email).trim().toLowerCase());
        }
    }
    return e.next();
});
