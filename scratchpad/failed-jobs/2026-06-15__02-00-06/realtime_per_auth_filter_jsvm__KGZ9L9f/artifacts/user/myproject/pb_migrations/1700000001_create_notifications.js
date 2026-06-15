/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const users = app.findCollectionByNameOrId("users");

    const notifications = new Collection({
        type: "base",
        name: "notifications",
        listRule: "recipient = @request.auth.id",
        viewRule: "recipient = @request.auth.id",
        fields: [
            {
                name: "recipient",
                type: "relation",
                required: true,
                collectionId: users.id,
                maxSelect: 1,
            },
            {
                name: "message",
                type: "text",
            }
        ]
    });

    app.save(notifications);
}, (app) => {
    try {
        const notifications = app.findCollectionByNameOrId("notifications");
        app.delete(notifications);
    } catch (e) { /* ignore */ }
});
