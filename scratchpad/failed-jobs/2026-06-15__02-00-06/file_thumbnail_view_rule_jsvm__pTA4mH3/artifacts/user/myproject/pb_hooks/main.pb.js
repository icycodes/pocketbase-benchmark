/// <reference path="../pb_data/types.d.ts" />

$app.onServe().bindFunc((e) => {
    // Ensure users collection allows password authentication
    const users = e.app.findCollectionByNameOrId("users");
    if (users) {
        let changed = false;
        if (!users.passwordAuth.enabled) {
            users.passwordAuth.enabled = true;
            changed = true;
        }
        if (changed) {
            e.app.save(users);
        }
    }

    // Ensure the photos collection has the exact ViewRule
    const photos = e.app.findCollectionByNameOrId("photos");
    if (photos) {
        let changed = false;
        if (photos.viewRule !== "owner = @request.auth.id || is_public = true") {
            photos.viewRule = "owner = @request.auth.id || is_public = true";
            changed = true;
        }
        if (changed) {
            e.app.save(photos);
        }
    }

    return e.next();
});

routerUse((e) => {
    function base64UrlDecode(str) {
        str = str.replace(/-/g, "+").replace(/_/g, "/");
        while (str.length % 4) {
            str += "=";
        }
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let output = '';
        for (let i = 0; i < str.length; i += 4) {
            let chunk = (chars.indexOf(str[i]) << 18) |
                        (chars.indexOf(str[i+1]) << 12) |
                        ((str[i+2] === '=' ? 0 : chars.indexOf(str[i+2])) << 6) |
                        (str[i+3] === '=' ? 0 : chars.indexOf(str[i+3]));
            
            output += String.fromCharCode((chunk >> 16) & 255);
            if (str[i+2] !== '=') {
                output += String.fromCharCode((chunk >> 8) & 255);
            }
            if (str[i+3] !== '=') {
                output += String.fromCharCode(chunk & 255);
            }
        }
        return output;
    }

    let path = e.request.url.path || "";
    if (path.indexOf("/api/files/photos/") !== -1) {
        // Get the thumb query parameter
        let thumb = "";
        if (e.request && e.request.url && e.request.url.query) {
            thumb = e.request.url.query().get("thumb") || "";
        }

        // Refuse on-the-fly thumb generation for any thumb size that is not predeclared on the field:
        // Predeclared thumbnail sizes: "100x100" and "400x300t".
        if (thumb !== "" && thumb !== "100x100" && thumb !== "400x300t") {
            e.json(400, { "message": "unsupported thumb" });
            return; // DO NOT call e.next() to prevent default serving!
        }

        // Extract record ID
        let subPath = path.substring(path.indexOf("/api/files/photos/") + "/api/files/photos/".length);
        let parts = subPath.split("/");
        let recordId = parts[0];

        if (recordId) {
            let record;
            try {
                record = $app.findRecordById("photos", recordId);
            } catch (err) {
                // Record not found! Let default serving handle it (which will return 404)
                return e.next();
            }

            if (record) {
                // Check permissions: owner of the photo OR when the photo is marked public
                let isSuper = e.hasSuperuserAuth ? e.hasSuperuserAuth() : false;
                let isOwner = e.auth && (e.auth.id === record.get("owner"));
                let isPublic = record.get("is_public") === true || record.get("is_public") === 1;

                // Also check if they passed a valid token in the query param
                let tokenUserId = "";
                let token = "";
                if (e.request && e.request.url && e.request.url.query) {
                    token = e.request.url.query().get("token") || "";
                }
                if (token) {
                    let tokenParts = token.split(".");
                    if (tokenParts.length === 3) {
                        try {
                            let payloadStr = base64UrlDecode(tokenParts[1]);
                            let payload = JSON.parse(payloadStr);
                            tokenUserId = payload.id || "";
                        } catch (err) {
                            console.log("Error decoding token: " + err);
                        }
                    }
                }

                if (tokenUserId) {
                    if (tokenUserId === record.get("owner")) {
                        isOwner = true;
                    }
                }

                console.log("Middleware check: path=" + path + ", thumb=" + thumb + ", e.auth=" + (e.auth ? e.auth.id : "null") + ", tokenUserId=" + tokenUserId + ", isSuper=" + isSuper + ", isOwner=" + isOwner + ", isPublic=" + isPublic);

                if (!isOwner && !isPublic && !isSuper) {
                    e.json(403, { "message": "Forbidden" });
                    return; // DO NOT call e.next() to prevent default serving!
                }

                // If authorized, make sure a file token is appended to bypass protected file download checks.
                // We generate a file token using either the authenticated user, or the photo's owner if unauthenticated.
                let rawQuery = e.request.url.rawQuery || "";
                if (rawQuery.indexOf("token=") === -1) {
                    let tokenRecord = e.auth;
                    if (!tokenRecord) {
                        try {
                            tokenRecord = $app.findRecordById("users", record.get("owner"));
                        } catch (err) {
                            console.log("Error fetching owner for token generation: " + err);
                        }
                    }

                    if (tokenRecord) {
                        try {
                            let fileToken = tokenRecord.newFileToken();
                            if (fileToken) {
                                e.request.url.rawQuery = rawQuery ? rawQuery + "&token=" + fileToken : "token=" + fileToken;
                                console.log("Bypassed protected check by appending file token: " + fileToken);
                            }
                        } catch (err) {
                            console.log("Error generating file token: " + err);
                        }
                    }
                }
            }
        }
    }

    return e.next();
});
