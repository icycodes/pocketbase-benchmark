/// <reference path="../pb_data/types.d.ts" />
migrate(
  (app) => {
    const users = new Collection({
      type: "auth",
      name: "users",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "id = @request.auth.id",
      deleteRule: "id = @request.auth.id",
      fields: [
        { name: "name", type: "text", max: 255 },
      ],
    });
    app.save(users);

    const categories = new Collection({
      type: "base",
      name: "categories",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "name", type: "text", required: true, max: 255 },
      ],
    });
    app.save(categories);

    const posts = new Collection({
      type: "base",
      name: "posts",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "title", type: "text", required: true, max: 255 },
        {
          name: "category",
          type: "relation",
          required: true,
          collectionId: categories.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
        {
          name: "author",
          type: "relation",
          required: false,
          collectionId: users.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
      ],
    });
    app.save(posts);

    const comments = new Collection({
      type: "base",
      name: "comments",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "content", type: "text", required: true, max: 5000 },
        {
          name: "post",
          type: "relation",
          required: true,
          collectionId: posts.id,
          maxSelect: 1,
          cascadeDelete: true,
        },
        {
          name: "author",
          type: "relation",
          required: true,
          collectionId: users.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
      ],
    });
    app.save(comments);
  },
  (app) => {
    for (const name of ["comments", "posts", "categories", "users"]) {
      try {
        const c = app.findCollectionByNameOrId(name);
        app.delete(c);
      } catch (e) {}
    }
  }
);
