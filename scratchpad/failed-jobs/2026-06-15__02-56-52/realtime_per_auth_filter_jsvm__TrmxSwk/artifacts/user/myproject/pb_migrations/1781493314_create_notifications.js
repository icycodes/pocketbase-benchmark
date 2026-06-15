/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const users = app.findCollectionByNameOrId("users");

    const collection = new Collection({
        name: "notifications",
        type: "base",
        listRule: "recipient = @request.auth.id",
        viewRule: "recipient = @request.auth.id",
    });

    collection.fields.add(new Field({
        name: "id",
        type: "text",
        primaryKey: true,
        required: true,
        system: true,
        pattern: "^[a-z0-9]+$"
    }));

    collection.fields.add(new RelationField({
        name: "recipient",
        collectionId: users.id,
        maxSelect: 1,
        required: true
    }));

    collection.fields.add(new TextField({
        name: "message",
        required: false
    }));

    app.save(collection);
}, (app) => {
    const collection = app.findCollectionByNameOrId("notifications");
    app.delete(collection);
})