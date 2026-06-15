/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const users = app.findCollectionByNameOrId("users");

    const notifications = new Collection({
        type: "base",
        name: "notifications",
        listRule: "recipient = @request.auth.id",
        viewRule: "recipient = @request.auth.id",
        createRule: null,
        updateRule: null,
        deleteRule: null,
        fields: [
            {
                name: "recipient",
                type: "relation",
                required: true,
                maxSelect: 1,
                collectionId: users.id,
                cascadeDelete: false,
            },
            {
                name: "message",
                type: "text",
                required: false,
            },
        ],
    });

    app.save(notifications);
}, (app) => {
    try {
        const notifications = app.findCollectionByNameOrId("notifications");
        app.delete(notifications);
    } catch (e) { /* ignore */ }
})
