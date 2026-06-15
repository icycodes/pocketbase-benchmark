/// <reference path="../pb_data/types.d.ts" />

migrate(
  (app) => {
    // ------------------------------------------------------------------
    // Resolve the built-in `users` auth collection ID at runtime.
    // ------------------------------------------------------------------
    const usersCollection = app.findCollectionByNameOrId("users");

    // ================================================================
    // 1.  `projects` collection
    //     fields : name (text, required)
    //              members (relation → users, multiple)
    //     rules  : members-based relational access control
    // ================================================================
    const projectsCollection = new Collection({
      name: "projects",
      type: "base",
      // We set rules inline; saveNoValidate bypasses rule→field
      // resolution that fails when fields are new in the same save.
      listRule:   "@request.auth.id ?= members",
      viewRule:   "@request.auth.id ?= members",
      createRule: "@request.auth.id != ''",
      updateRule: "@request.auth.id ?= members",
      deleteRule: "@request.auth.id ?= members",
      fields: [
        {
          name: "name",
          type: "text",
          required: true,
        },
        {
          name: "members",
          type: "relation",
          collectionId: usersCollection.id,
          cascadeDelete: false,
          maxSelect: 999, // > 1 → multi-value / multiple relation
          required: false,
        },
      ],
    });

    app.saveNoValidate(projectsCollection);

    // ================================================================
    // 2.  `tasks` collection
    //     fields : title (text, required)
    //              project (relation → projects, single, required)
    //     rules  : @request.auth.id ?= project.members
    // ================================================================
    const tasksCollection = new Collection({
      name: "tasks",
      type: "base",
      listRule:   "@request.auth.id ?= project.members",
      viewRule:   "@request.auth.id ?= project.members",
      createRule: "@request.auth.id ?= project.members",
      updateRule: "@request.auth.id ?= project.members",
      deleteRule: "@request.auth.id ?= project.members",
      fields: [
        {
          name: "title",
          type: "text",
          required: true,
        },
        {
          name: "project",
          type: "relation",
          collectionId: projectsCollection.id,
          cascadeDelete: true,
          maxSelect: 1, // single relation
          required: true,
        },
      ],
    });

    app.saveNoValidate(tasksCollection);
  },

  // ------------------------------------------------------------------
  // Down migration
  // ------------------------------------------------------------------
  (app) => {
    for (const name of ["tasks", "projects"]) {
      try {
        app.delete(app.findCollectionByNameOrId(name));
      } catch (_) {}
    }
  }
);
