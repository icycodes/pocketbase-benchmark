/// <reference path="../pb_data/types.d.ts" />

// Predeclared thumbnail sizes for the photos collection image field.
// These MUST match the thumbs configured on the field in the migration.
const ALLOWED_THUMBS = ["100x100", "400x300t"];

onFileDownloadRequest((e) => {
    // Only enforce for the photos collection.
    if (!e.collection || e.collection.name !== "photos") {
        return e.next();
    }

    // Extract the "thumb" query parameter from the request URL.
    const url = e.request.url;
    const thumbParam = url.query().get("thumb");

    // If no thumb parameter, let the normal flow handle it (ViewRule applies).
    if (!thumbParam) {
        return e.next();
    }

    // If the thumb size is not in the predeclared list, reject with 400.
    if (ALLOWED_THUMBS.indexOf(thumbParam) === -1) {
        return e.json(400, { message: "unsupported thumb" });
    }

    // Valid thumb size - let the normal flow handle it.
    return e.next();
}, "photos");
