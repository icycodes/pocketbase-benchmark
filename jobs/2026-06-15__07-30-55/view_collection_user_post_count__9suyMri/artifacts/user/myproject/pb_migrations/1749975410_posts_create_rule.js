/// <reference path="../pb_hooks/types.d.ts" />

migrate(
  (app) => {
    // Allow authenticated users to create posts
    const posts = app.findCollectionByNameOrId("posts");
    posts.createRule = "@request.auth.id != ''";
    app.save(posts);
  },

  (app) => {
    const posts = app.findCollectionByNameOrId("posts");
    posts.createRule = null;
    app.save(posts);
  }
);
