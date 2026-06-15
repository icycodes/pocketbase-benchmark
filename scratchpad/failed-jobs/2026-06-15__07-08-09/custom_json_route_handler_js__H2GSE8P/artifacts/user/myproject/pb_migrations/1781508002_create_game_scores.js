migrate((app) => {
  const collection = new Collection({
    type: "base",
    name: "game_scores",
    listRule: "",
    viewRule: "",
    createRule: "",
    updateRule: null,
    deleteRule: null,
    fields: [
      {
        name: "score",
        type: "number",
        required: true,
      }
    ]
  });
  app.save(collection);
}, (app) => {
  try {
    const collection = app.findCollectionByNameOrId("game_scores");
    app.delete(collection);
  } catch (err) {
    // Ignore
  }
});
