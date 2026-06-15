migrate(
  (app) => {
    // Resolve the built-in users collection id
    const usersCollection = app.findCollectionByNameOrId("users");

    // ── projects collection ───────────────────────────────────────────────────
    const projects = new Collection({
      type: "base",
      name: "projects",
      listRule: "members.id ?= @request.auth.id",
      viewRule: "members.id ?= @request.auth.id",
      createRule: "@request.auth.id != ''",
      updateRule: "members.id ?= @request.auth.id",
      deleteRule: "members.id ?= @request.auth.id",
      fields: [
        {
          name: "name",
          type: "text",
          required: true,
          min: 1,
        },
        {
          name: "members",
          type: "relation",
          required: true,
          collectionId: usersCollection.id,
          minSelect: 1,
          maxSelect: 999, // large number = effectively unlimited multi-select
        },
      ],
    });

    app.save(projects);

    // ── tasks collection ──────────────────────────────────────────────────────
    const tasks = new Collection({
      type: "base",
      name: "tasks",
      listRule:
        "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      viewRule:
        "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      createRule:
        "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      updateRule:
        "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      deleteRule:
        "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      fields: [
        {
          name: "title",
          type: "text",
          required: true,
          min: 1,
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
          collectionId: projects.id,
          minSelect: 1,
          maxSelect: 1, // single relation
        },
      ],
    });

    app.save(tasks);
  },
  (app) => {
    // down – drop both collections in reverse order to respect FK constraints
    try {
      const tasks = app.findCollectionByNameOrId("tasks");
      app.delete(tasks);
    } catch (_) {}

    try {
      const projects = app.findCollectionByNameOrId("projects");
      app.delete(projects);
    } catch (_) {}
  }
);
