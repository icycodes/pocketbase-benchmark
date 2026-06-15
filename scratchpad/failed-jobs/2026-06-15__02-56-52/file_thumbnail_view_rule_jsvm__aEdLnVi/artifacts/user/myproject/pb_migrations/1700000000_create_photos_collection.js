/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
    const dao = new Dao(db)
    const users = dao.findCollectionByNameOrId("users")

    const collection = new Collection({
        type: "base",
        name: "photos",
        listRule: "owner = @request.auth.id || is_public = true",
        viewRule: "owner = @request.auth.id || is_public = true",
        createRule: "@request.auth.id != \"\"",
        updateRule: "owner = @request.auth.id",
        deleteRule: "owner = @request.auth.id",
        schema: [
            {
                name: "owner",
                type: "relation",
                required: true,
                options: {
                    collectionId: users.id,
                    cascadeDelete: true,
                    maxSelect: 1,
                }
            },
            {
                name: "image",
                type: "file",
                required: true,
                options: {
                    maxSelect: 1,
                    maxSize: 5242880,
                    mimeTypes: ["image/png", "image/jpeg", "image/gif", "image/webp"],
                    thumbs: ["100x100", "400x300t"],
                    protected: true,
                }
            },
            {
                name: "is_public",
                type: "bool",
                required: false,
            },
        ],
    })

    dao.saveCollection(collection)
}, (db) => {
    const dao = new Dao(db)
    const collection = dao.findCollectionByNameOrId("photos")
    dao.deleteCollection(collection)
})
