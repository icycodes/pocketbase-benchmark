/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const users = app.findCollectionByNameOrId("users")

    const collection = new Collection({
        type: "base",
        name: "photos",
        listRule: "owner = @request.auth.id || is_public = true",
        viewRule: "owner = @request.auth.id || is_public = true",
        createRule: "@request.auth.id != \"\"",
        updateRule: "owner = @request.auth.id",
        deleteRule: "owner = @request.auth.id",
        fields: [
            {
                name: "owner",
                type: "relation",
                required: true,
                collectionId: users.id,
                cascadeDelete: true,
                maxSelect: 1,
            },
            {
                name: "image",
                type: "file",
                required: true,
                maxSelect: 1,
                maxSize: 5242880,
                mimeTypes: ["image/png", "image/jpeg", "image/gif", "image/webp"],
                thumbs: ["100x100", "400x300t"],
                protected: true,
            },
            {
                name: "is_public",
                type: "bool",
                required: false,
            },
        ],
    })

    app.save(collection)
}, (app) => {
    const collection = app.findCollectionByNameOrId("photos")
    app.delete(collection)
})
