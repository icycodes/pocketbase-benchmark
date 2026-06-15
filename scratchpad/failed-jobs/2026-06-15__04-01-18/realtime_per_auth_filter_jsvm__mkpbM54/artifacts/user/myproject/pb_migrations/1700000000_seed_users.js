/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const users = app.findCollectionByNameOrId("users");

    const alice = new Record(users);
    alice.set("email", "alice@example.com");
    alice.set("emailVisibility", true);
    alice.set("verified", true);
    alice.set("name", "Alice");
    alice.setPassword("AlicePass1234");
    app.save(alice);

    const bob = new Record(users);
    bob.set("email", "bob@example.com");
    bob.set("emailVisibility", true);
    bob.set("verified", true);
    bob.set("name", "Bob");
    bob.setPassword("BobPass1234");
    app.save(bob);
}, (app) => {
    try {
        const alice = app.findAuthRecordByEmail("users", "alice@example.com");
        app.delete(alice);
    } catch (e) { /* ignore */ }
    try {
        const bob = app.findAuthRecordByEmail("users", "bob@example.com");
        app.delete(bob);
    } catch (e) { /* ignore */ }
})
