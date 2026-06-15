/// <reference path="../pb_data/types.d.ts" />

// Idempotent migration: creates the "tasks" collection only if it does not exist.
migrate(
  (app) => {
    // Skip if already created
    try {
      app.findCollectionByNameOrId("tasks");
      return; // collection exists – nothing to do
    } catch (_) {}

    const collection = new Collection({
      name: "tasks",
      type: "base",
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
        },
      ],
    });

    app.save(collection);
  },
  (app) => {
    // Revert: drop the collection if it exists
    try {
      const collection = app.findCollectionByNameOrId("tasks");
      app.delete(collection);
    } catch (_) {}
  }
);
