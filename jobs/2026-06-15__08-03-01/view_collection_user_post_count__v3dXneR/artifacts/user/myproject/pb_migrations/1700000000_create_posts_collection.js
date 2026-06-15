/// <reference path="../pb_data/types.d.ts" />

migrate(
  (txApp) => {
    const collection = new Collection({
      type: "base",
      name: "posts",
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
          collectionId: "_pb_users_auth_",
          cascadeDelete: false,
          minSelect: 0,
          maxSelect: 1,
          required: false,
        },
      ],
    });

    txApp.save(collection);
  },
  (txApp) => {
    const collection = txApp.findCollectionByNameOrId("posts");
    txApp.delete(collection);
  }
);