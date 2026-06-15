migrate((app) => {
  let collection = new Collection({
    type: "base",
    name: "posts",
    createRule: "", // allow public create access
    fields: [
      {
        name: "title",
        type: "text",
      },
      {
        name: "slug",
        type: "text",
      },
    ],
  });
  app.save(collection);
}, (app) => {
  try {
    let collection = app.findCollectionByNameOrId("posts");
    app.delete(collection);
  } catch (e) {}
});
