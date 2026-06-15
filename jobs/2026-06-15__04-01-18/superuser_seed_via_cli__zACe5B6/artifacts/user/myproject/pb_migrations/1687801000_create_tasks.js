/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    // Check if collection already exists (idempotency)
    try {
        let existing = app.findCollectionByNameOrId("tasks");
        // Collection already exists, skip creation
        return;
    } catch {
        // Collection doesn't exist, create it
    }

    let collection = new Collection({
        type: "base",
        name: "tasks",
        fields: [
            {
                type: "text",
                name: "title",
                required: true,
            },
            {
                type: "bool",
                name: "done",
            },
            {
                type: "date",
                name: "due",
            },
        ],
        listRule: "",
        viewRule: "",
        createRule: "",
        updateRule: "",
        deleteRule: "",
    });

    app.save(collection);
}, (app) => {
    // Down migration: delete the tasks collection
    try {
        let collection = app.findCollectionByNameOrId("tasks");
        app.delete(collection);
    } catch {
        // silently ignore if already deleted
    }
});
