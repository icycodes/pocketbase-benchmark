onRecordBeforeCreateRequest((e) => {
    const email = e.record.getString("email");
    if (email) {
        e.record.set("email", email.trim().toLowerCase());
    }
    e.next();
}, "users");