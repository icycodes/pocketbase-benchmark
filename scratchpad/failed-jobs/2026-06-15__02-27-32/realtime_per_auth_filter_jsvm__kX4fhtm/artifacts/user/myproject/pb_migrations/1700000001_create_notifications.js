/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    // Look up the users collection to get its ID for the relation field
    const usersCol = app.findCollectionByNameOrId("users");

    const collection = new Collection({
        name:    "notifications",
        type:    "base",

        // Only the authenticated user whose id matches recipient can list/view
        listRule: "recipient = @request.auth.id",
        viewRule: "recipient = @request.auth.id",

        // create/update/delete restricted to superusers (null = superuser only)
        createRule: null,
        updateRule: null,
        deleteRule: null,

        fields: [
            {
                name:          "recipient",
                type:          "relation",
                required:      true,
                collectionId:  usersCol.id,
                cascadeDelete: false,
                maxSelect:     1,
            },
            {
                name:     "message",
                type:     "text",
                required: false,
            },
        ],
    });

    app.save(collection);
}, (app) => {
    try {
        const collection = app.findCollectionByNameOrId("notifications");
        app.delete(collection);
    } catch (e) { /* ignore */ }
});
