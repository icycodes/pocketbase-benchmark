migrate((app) => {
  const collection = new Collection({
    id: "game_scores_collection",
    name: "game_scores",
    type: "base",
    fields: [
      {
        id: "score_field",
        name: "score",
        type: "number"
      }
    ],
    listRule: "",
    viewRule: "",
    createRule: "",
    updateRule: "",
    deleteRule: ""
  });

  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("game_scores");
  app.delete(collection);
});
