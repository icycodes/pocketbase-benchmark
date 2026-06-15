/// <reference path="../pb_data/types.d.ts" />

migrate(
  (app) => {
    const collection = new Collection({
      name: "game_scores",
      type: "base",
      fields: [
        {
          system: false,
          id: "score_field",
          name: "score",
          type: "number",
          required: false,
        },
      ],
      indexes: [],
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: null,
      deleteRule: null,
    });

    app.save(collection);
  },
  (app) => {
    const collection = app.findCollectionByNameOrId("game_scores");
    app.delete(collection);
  }
);