/// <reference path="../pb_data/types.d.ts" />

// Hook: enforce ViewRule and thumb whitelist for the photos collection.
//
// Behaviour matrix for GET /api/files/photos/<recordId>/<filename>[?thumb=...]
//
//  thumb param       | auth passes ViewRule | result
//  ------------------|----------------------|---------------------------
//  absent            | yes                  | 200 original bytes
//  absent            | no                   | 403
//  allowed size      | yes                  | 200 thumb bytes
//  allowed size      | no                   | 403
//  disallowed size   | any                  | 400 {"message":"unsupported thumb"}
//
// Allowed thumb sizes: 100x100, 400x300t

onFileDownloadRequest((e) => {
    // Only intercept the photos collection
    if (!e.collection || e.collection.name !== "photos") {
        return e.next();
    }

    const info  = e.requestInfo();
    const thumb = info.query["thumb"] || "";

    // ── Thumb whitelist check (takes priority, regardless of auth) ──────────
    if (thumb) {
        const allowed = ["100x100", "400x300t"];
        if (allowed.indexOf(thumb) === -1) {
            return e.json(400, { message: "unsupported thumb" });
        }
    }

    // ── ViewRule enforcement ────────────────────────────────────────────────
    // ViewRule: owner = @request.auth.id || is_public = true
    const record   = e.record;
    const authUser = e.auth;

    const isPublic = record.getBool("is_public");
    if (isPublic) {
        return e.next(); // public photo: anyone can access
    }

    // Not public → must be the authenticated owner
    if (!authUser) {
        throw new ForbiddenError("Unauthorized");
    }

    const ownerId = record.getString("owner");
    if (authUser.id !== ownerId) {
        throw new ForbiddenError("Unauthorized");
    }

    return e.next();
});
