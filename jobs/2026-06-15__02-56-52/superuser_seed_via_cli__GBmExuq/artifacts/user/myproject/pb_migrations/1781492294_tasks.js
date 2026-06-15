/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = new Collection({
    type: "base",
    name: "tasks",
    fields: [
      {
        name: "title",
        type: "text",
        required: true
      },
      {
        name: "done",
        type: "bool"
      },
      {
        name: "due",
        type: "date"
      }
    ]
  });
  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("tasks");
  app.delete(collection);
})