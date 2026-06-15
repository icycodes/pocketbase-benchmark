/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const users = app.findCollectionByNameOrId("users");

  // Check if users has a 'username' field
  let hasUsername = false;
  for (let f of users.fields) {
    if (f.name === "username") {
      hasUsername = true;
      break;
    }
  }

  if (!hasUsername) {
    users.fields.add(new TextField({
      name: "username",
      required: true,
    }));
    app.save(users);
  }

  // Create 'posts' collection
  const posts = new Collection({
    name: "posts",
    type: "base",
    listRule: "",
    viewRule: "",
    createRule: "",
    updateRule: "",
    deleteRule: "",
    fields: [
      {
        name: "title",
        type: "text",
        required: false,
      },
      {
        name: "author",
        type: "relation",
        required: true,
        maxSelect: 1,
        collectionId: users.id,
        cascadeDelete: true,
      }
    ]
  });

  app.save(posts);

  // Create 'user_post_counts' view collection
  const view = new Collection({
    name: "user_post_counts",
    type: "view",
    listRule: "",
    viewRule: "",
    viewQuery: `
      SELECT
        users.id,
        users.username,
        COUNT(posts.id) as post_count
      FROM users
      LEFT JOIN posts ON posts.author = users.id
      GROUP BY users.id
    `,
    fields: [
      {
        name: "id",
        type: "text",
      },
      {
        name: "username",
        type: "text",
      },
      {
        name: "post_count",
        type: "number",
      }
    ]
  });

  app.save(view);
}, (app) => {
  try {
    const view = app.findCollectionByNameOrId("user_post_counts");
    app.delete(view);
  } catch (e) {}

  try {
    const posts = app.findCollectionByNameOrId("posts");
    app.delete(posts);
  } catch (e) {}
});
