/// <reference path="../pb_data/types.d.ts" />

onRecordCreateRequest((e) => {
    const email = e.record.get("email");

    if (typeof email === "string") {
        e.record.set("email", email.trim().toLowerCase());
    }

    e.next();
}, "users");
