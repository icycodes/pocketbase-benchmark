/// <reference path="../pb_hooks/types.d.ts" />

migrate(
  (app) => {
    // Allow public (unauthenticated) listing of user_post_counts
    const view = app.findCollectionByNameOrId("user_post_counts");
    view.listRule = "";
    view.viewRule = "";
    app.save(view);

    // Allow public listing/viewing of posts; authenticated users can create
    const posts = app.findCollectionByNameOrId("posts");
    posts.listRule = "";
    posts.viewRule = "";
    posts.createRule = "@request.auth.id != ''";
    app.save(posts);
  },

  (app) => {
    // Revert rules to null (superusers only)
    const view = app.findCollectionByNameOrId("user_post_counts");
    view.listRule = null;
    view.viewRule = null;
    app.save(view);

    const posts = app.findCollectionByNameOrId("posts");
    posts.listRule = null;
    posts.viewRule = null;
    app.save(posts);
  }
);
