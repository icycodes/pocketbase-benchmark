/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    // Create or update the superuser
    const superusers = app.findCollectionByNameOrId("_superusers")
    let su
    try {
        su = app.findAuthRecordByEmail("_superusers", "admin@example.com")
    } catch (_) {
        su = new Record(superusers)
        su.set("email", "admin@example.com")
    }
    su.set("password", "Admin12345!")
    app.save(su)

    // Ensure the users auth collection has password authentication enabled
    const users = app.findCollectionByNameOrId("users")
    users.passwordAuth.enabled = true
    app.save(users)
}, (app) => {
    try {
        const record = app.findAuthRecordByEmail("_superusers", "admin@example.com")
        app.delete(record)
    } catch (_) {}
})
