/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    // Create the game_scores collection
    const collection = new Collection({
        name: "game_scores",
        type: "base",
        listRule: "",
        viewRule: "",
        createRule: "",
        updateRule: null,
        deleteRule: null,
        fields: [
            {
                name: "score",
                type: "number",
                required: false,
            },
        ],
    });

    app.save(collection);
}, (app) => {
    // Down: delete the collection
    const collection = app.findCollectionByNameOrId("game_scores");
    app.delete(collection);
});
