migrate((app) => {
    // 1. Resolve users collection ID
    const usersCollection = app.findCollectionByNameOrId("users");

    // 2. Create projects collection
    const projectsCollection = new Collection({
        type: "base",
        name: "projects",
        listRule: "@request.auth.id != '' && members.id ?= @request.auth.id",
        viewRule: "@request.auth.id != '' && members.id ?= @request.auth.id",
        createRule: "@request.auth.id != ''",
        updateRule: "@request.auth.id != '' && members.id ?= @request.auth.id",
        deleteRule: "@request.auth.id != '' && members.id ?= @request.auth.id",
        fields: [
            {
                name: "name",
                type: "text",
                required: true,
            },
            {
                name: "members",
                type: "relation",
                required: true,
                collectionId: usersCollection.id,
                maxSelect: 999999, // multi-select with no practical limit
            }
        ]
    });
    app.save(projectsCollection);

    // 3. Create tasks collection
    const tasksCollection = new Collection({
        type: "base",
        name: "tasks",
        listRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
        viewRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
        createRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
        updateRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
        deleteRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
        fields: [
            {
                name: "title",
                type: "text",
                required: true,
            },
            {
                name: "description",
                type: "text",
                required: false,
            },
            {
                name: "project",
                type: "relation",
                required: true,
                maxSelect: 1, // single-relation
                collectionId: projectsCollection.id,
            }
        ]
    });
    app.save(tasksCollection);
}, (app) => {
    // Revert/rollback
    try {
        const tasksCollection = app.findCollectionByNameOrId("tasks");
        app.delete(tasksCollection);
    } catch (e) {}

    try {
        const projectsCollection = app.findCollectionByNameOrId("projects");
        app.delete(projectsCollection);
    } catch (e) {}
});
