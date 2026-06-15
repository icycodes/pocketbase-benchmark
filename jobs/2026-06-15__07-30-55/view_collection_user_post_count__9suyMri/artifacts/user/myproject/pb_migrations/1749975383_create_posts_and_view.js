/// <reference path="../pb_hooks/types.d.ts" />

migrate(
  (app) => {
    // -------------------------------------------------------
    // 1. posts collection
    // -------------------------------------------------------

    // Resolve the real ID of the built-in users auth collection at runtime
    const usersCollection = app.findCollectionByNameOrId("users");

    const postsCollection = new Collection({
      name: "posts",
      type: "base",
      fields: [
        {
          name: "author",
          type: "relation",
          required: false,
          collectionId: usersCollection.id,
          cascadeDelete: false,
          maxSelect: 1,
        },
      ],
    });

    app.save(postsCollection);

    // -------------------------------------------------------
    // 2. user_post_counts view collection
    //
    // The users auth collection stores the display name in the
    // "name" column; we expose it as "username" via aliasing.
    // Fields are derived automatically from the view query.
    // -------------------------------------------------------
    const viewCollection = new Collection({
      name: "user_post_counts",
      type: "view",
      viewQuery: `SELECT users.id AS id, users.name AS username, COUNT(posts.id) AS post_count FROM users LEFT JOIN posts ON posts.author = users.id GROUP BY users.id`,
    });

    app.save(viewCollection);
  },

  (app) => {
    // down – remove view first, then posts
    try {
      const view = app.findCollectionByNameOrId("user_post_counts");
      app.delete(view);
    } catch (_) {}

    try {
      const posts = app.findCollectionByNameOrId("posts");
      app.delete(posts);
    } catch (_) {}
  }
);
