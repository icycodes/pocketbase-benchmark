/// <reference path="../pb_data/types.d.ts" />

onRecordCreateRequest((e) => {
    if (e.record && e.collection && e.collection.name === "users") {
        var email = e.record.get("email");
        if (email && typeof email === "string") {
            var cleanEmail = email.trim().toLowerCase();
            e.record.set("email", cleanEmail);
        }
    }
    e.next();
}, "users");
