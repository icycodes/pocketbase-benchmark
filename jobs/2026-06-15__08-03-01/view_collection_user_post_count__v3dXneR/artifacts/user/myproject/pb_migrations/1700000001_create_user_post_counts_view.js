/// <reference path="../pb_data/types.d.ts" />

migrate(
  (txApp) => {
    const collection = new Collection({
      type: "view",
      name: "user_post_counts",
      listRule: "",
      viewRule: "",
      fields: [
        {
          name: "id",
          type: "relation",
          collectionId: "_pb_users_auth_",
          cascadeDelete: false,
          minSelect: 0,
          maxSelect: 1,
          required: true,
        },
        {
          name: "username",
          type: "text",
          required: false,
        },
        {
          name: "post_count",
          type: "number",
          required: false,
        },
      ],
      viewQuery:
        "SELECT users.id, users.name as username, COUNT(posts.id) as post_count FROM users LEFT JOIN posts ON posts.author = users.id GROUP BY users.id, users.name",
    });

    txApp.save(collection);
  },
  (txApp) => {
    const collection = txApp.findCollectionByNameOrId("user_post_counts");
    txApp.delete(collection);
  }
);