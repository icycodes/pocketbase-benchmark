migrate((app) => {
  let collection = new Collection({
    type: "base",
    name: "tasks",
    fields: [
      {
        name: "title",
        type: "text",
        required: true,
      },
      {
        name: "done",
        type: "bool",
      },
      {
        name: "due",
        type: "date",
      }
    ]
  });
  app.save(collection);
}, (app) => {
  let collection = app.findCollectionByNameOrId("tasks");
  app.delete(collection);
});
