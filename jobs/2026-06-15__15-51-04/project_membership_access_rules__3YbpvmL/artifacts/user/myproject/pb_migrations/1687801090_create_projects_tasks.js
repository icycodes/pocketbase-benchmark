migrate((app) => {
    // Resolve the built-in users collection id for the relation field
    const usersCollectionId = app.findCollectionByNameOrId("users").id;

    // --- projects collection ---
    const projects = new Collection({
        type: "base",
        name: "projects",
        listRule:   '@request.auth.id != "" && members.id ?= @request.auth.id',
        viewRule:   '@request.auth.id != "" && members.id ?= @request.auth.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id != "" && members.id ?= @request.auth.id',
        deleteRule: '@request.auth.id != "" && members.id ?= @request.auth.id',
        fields: [
            {
                name:     "name",
                type:     "text",
                required: true,
                max:      255,
                min:      1,
            },
            {
                name:         "members",
                type:         "relation",
                required:     true,
                collectionId: usersCollectionId,
                cascadeDelete: false,
                maxSelect:    999,
            },
        ],
    });

    app.save(projects);

    // --- tasks collection ---
    // We need the projects collection id, but since we just saved it,
    // we can look it up.
    const projectsCollectionId = app.findCollectionByNameOrId("projects").id;

    const tasks = new Collection({
        type: "base",
        name: "tasks",
        listRule:   '@request.auth.id != "" && project.members.id ?= @request.auth.id',
        viewRule:   '@request.auth.id != "" && project.members.id ?= @request.auth.id',
        createRule: '@request.auth.id != "" && project.members.id ?= @request.auth.id',
        updateRule: '@request.auth.id != "" && project.members.id ?= @request.auth.id',
        deleteRule: '@request.auth.id != "" && project.members.id ?= @request.auth.id',
        fields: [
            {
                name:     "title",
                type:     "text",
                required: true,
                max:      255,
                min:      1,
            },
            {
                name:     "description",
                type:     "text",
                required: false,
                max:      10000,
            },
            {
                name:         "project",
                type:         "relation",
                required:     true,
                collectionId: projectsCollectionId,
                cascadeDelete: false,
                maxSelect:    1,
            },
        ],
    });

    app.save(tasks);
}, (app) => {
    // Rollback: delete both collections
    try {
        const tasks = app.findCollectionByNameOrId("tasks");
        app.delete(tasks);
    } catch {
        // already deleted, ignore
    }
    try {
        const projects = app.findCollectionByNameOrId("projects");
        app.delete(projects);
    } catch {
        // already deleted, ignore
    }
});
