/// <reference path="../pb_data/types.d.ts" />

/**
 * Sanitizes the email field on the users collection before record creation.
 *
 * - Lowercases the email
 * - Trims leading and trailing whitespace
 */
onRecordCreateRequest((e) => {
    const email = e.record?.get("email");

    if (typeof email === "string" && email !== "") {
        e.record.set("email", email.toLowerCase().trim());
    }

    e.next();
}, "users");
