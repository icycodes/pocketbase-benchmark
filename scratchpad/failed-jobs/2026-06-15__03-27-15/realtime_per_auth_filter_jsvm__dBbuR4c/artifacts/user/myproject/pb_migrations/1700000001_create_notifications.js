/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const usersCollection = app.findCollectionByNameOrId("users");

    const collection = new Collection({
        name: "notifications",
        type: "base",
    });

    collection.listRule = "recipient = @request.auth.id";
    collection.viewRule = "recipient = @request.auth.id";

    collection.fields.add(
        new RelationField({
            name: "recipient",
            required: true,
            collectionId: usersCollection.id,
            maxSelect: 1,
        })
    );

    collection.fields.add(
        new TextField({
            name: "message",
        })
    );

    app.save(collection);
}, (app) => {
    try {
        const collection = app.findCollectionByNameOrId("notifications");
        app.delete(collection);
    } catch (e) { /* ignore */ }
})