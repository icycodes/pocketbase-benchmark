/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = new Collection({
    "id": "posts_collection_id",
    "name": "posts",
    "type": "base",
    "system": false,
    "listRule": "",
    "viewRule": "",
    "createRule": "",
    "updateRule": "",
    "deleteRule": ""
  });
  
  collection.fields.add(
    new TextField({
      name: "title",
      required: false
    }),
    new TextField({
      name: "slug",
      required: false
    })
  );

  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("posts");
  app.delete(collection);
})
