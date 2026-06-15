/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const users = app.findCollectionByNameOrId("users")

    const collection = new Collection({
        type:       "base",
        name:       "photos",
        listRule:   "owner = @request.auth.id || is_public = true",
        viewRule:   "owner = @request.auth.id || is_public = true",
        createRule: "@request.auth.id != \"\"",
        updateRule: "owner = @request.auth.id",
        deleteRule: "owner = @request.auth.id",
        fields: [
            {
                name:          "owner",
                type:          "relation",
                required:      true,
                collectionId:  users.id,
                cascadeDelete: true,
                maxSelect:     1,
            },
            {
                name:      "image",
                type:      "file",
                required:  true,
                maxSelect: 1,
                maxSize:   10485760,
                mimeTypes: [
                    "image/png",
                    "image/jpeg",
                    "image/gif",
                    "image/webp",
                    "image/svg+xml",
                ],
                thumbs:    ["100x100", "400x300t"],
                protected: false,
            },
            {
                name:     "is_public",
                type:     "bool",
                required: false,
            },
        ],
    })

    app.save(collection)
}, (app) => {
    try {
        const collection = app.findCollectionByNameOrId("photos")
        app.delete(collection)
    } catch (_) {}
})
