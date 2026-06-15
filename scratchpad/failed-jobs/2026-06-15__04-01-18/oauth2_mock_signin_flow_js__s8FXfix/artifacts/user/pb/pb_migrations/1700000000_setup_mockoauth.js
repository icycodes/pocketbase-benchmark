/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const collection = app.findCollectionByNameOrId("users");
    collection.oauth2.enabled = true;
    collection.oauth2.providers = [
        {
            name: "oidc",
            displayName: "mockoauth",
            clientId: "mock-client-id",
            clientSecret: "mock-client-secret",
            authURL: "http://127.0.0.1:9000/authorize",
            tokenURL: "http://127.0.0.1:9000/token",
            userInfoURL: "http://127.0.0.1:9000/userinfo"
        }
    ];
    app.save(collection);
}, (app) => {
    const collection = app.findCollectionByNameOrId("users");
    collection.oauth2.providers = (collection.oauth2.providers || []).filter(
        (p) => p.displayName !== "mockoauth"
    );
    app.save(collection);
});
