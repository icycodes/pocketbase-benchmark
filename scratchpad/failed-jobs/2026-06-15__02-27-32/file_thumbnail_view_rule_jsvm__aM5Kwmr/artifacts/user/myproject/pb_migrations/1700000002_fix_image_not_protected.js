/// <reference path="../pb_data/types.d.ts" />

// The image field was created with protected:true which requires signed tokens for
// file access rather than standard Authorization headers. Remove the protected flag
// so the ViewRule alone controls access (HTTP 200 for owners/public, 403 otherwise).
migrate((app) => {
    const collection = app.findCollectionByNameOrId("photos")
    const imageField = collection.fields.getByName("image")
    imageField.protected = false
    // Ensure all required mimeTypes are present
    imageField.mimeTypes = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ]
    imageField.thumbs = ["100x100", "400x300t"]
    imageField.maxSize = 10485760
    app.save(collection)
}, (app) => {
    const collection = app.findCollectionByNameOrId("photos")
    const imageField = collection.fields.getByName("image")
    imageField.protected = true
    app.save(collection)
})
