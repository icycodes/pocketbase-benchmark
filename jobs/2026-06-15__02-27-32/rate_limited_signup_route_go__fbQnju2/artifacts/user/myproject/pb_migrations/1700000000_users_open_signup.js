/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    // Ensure the users collection allows unauthenticated signup
    const collection = app.findCollectionByNameOrId("users");

    // Allow anyone to create (signup) without authentication
    collection.createRule = "";

    app.save(collection);
}, (app) => {
    // Revert: restore default create rule (only superusers)
    const collection = app.findCollectionByNameOrId("users");
    collection.createRule = null;
    app.save(collection);
});
