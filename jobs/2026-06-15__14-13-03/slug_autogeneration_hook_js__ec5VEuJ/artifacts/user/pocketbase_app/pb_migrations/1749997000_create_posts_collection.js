/// <reference path="../pb_data/types.d.ts" />
migrate(
  (app) => {
    const collection = new Collection({
      name: "posts",
      type: "base",
      fields: [
        {
          name: "title",
          type: "text",
          required: false,
        },
        {
          name: "slug",
          type: "text",
          required: false,
        },
      ],
      createRule: "",
      listRule: "",
      viewRule: "",
      updateRule: "",
      deleteRule: "",
    });

    return app.save(collection);
  },
  (app) => {
    const collection = app.findCollectionByNameOrId("posts");
    return app.delete(collection);
  }
);
