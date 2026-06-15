onRecordCreate((e) => {
    const email = e.record.get("email");
    if (email && typeof email === 'string') {
        e.record.set("email", email.trim().toLowerCase());
    }
    return e.next();
}, "users");
