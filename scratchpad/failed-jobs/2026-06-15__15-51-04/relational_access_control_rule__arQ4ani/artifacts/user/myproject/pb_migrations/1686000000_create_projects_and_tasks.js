/// <reference path="../pb_data/types.d.ts" />

migrate(
  (app) => {
    // ============================================================
    // Create the `projects` collection
    // ============================================================
    const projects = new Collection({
      name: "projects",
      type: "base",
      system: false,
      schema: [
        {
          name: "name",
          type: "text",
          required: true,
          options: {
            min: null,
            max: null,
            pattern: "",
          },
        },
        {
          name: "members",
          type: "relation",
          required: false,
          options: {
            collectionId: "_pb_users_auth_",
            cascadeDelete: false,
            maxSelect: null, // multiple users
            displayFields: [],
          },
        },
      ],
      listRule: "@request.auth.id != ''",
      viewRule: "@request.auth.id != ''",
      createRule: "@request.auth.id != ''",
      updateRule: "@request.auth.id != ''",
      deleteRule: "@request.auth.id != ''",
      indexes: [],
    });

    app.save(projects);

    // ============================================================
    // Create the `tasks` collection
    // ============================================================
    const tasks = new Collection({
      name: "tasks",
      type: "base",
      system: false,
      schema: [
        {
          name: "title",
          type: "text",
          required: true,
          options: {
            min: null,
            max: null,
            pattern: "",
          },
        },
        {
          name: "project",
          type: "relation",
          required: true,
          options: {
            collectionId: projects.id,
            cascadeDelete: false,
            maxSelect: 1,
            displayFields: [],
          },
        },
      ],
      // ----------------------------------------------------------
      // Relational access control:
      // A user can only list/view a task if they are in the
      // `members` array of the task's parent project.
      //
      // `project.members` resolves to the members relation field
      // of the related project record.
      // `?=` is the "any/at-least-one-of equal" operator.
      // ----------------------------------------------------------
      listRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      viewRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      createRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      updateRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      deleteRule: "@request.auth.id != '' && project.members.id ?= @request.auth.id",
      indexes: [],
    });

    app.save(tasks);
  },
  (app) => {
    const tasks = app.findCollectionByNameOrId("tasks");
    app.delete(tasks);
    const projects = app.findCollectionByNameOrId("projects");
    app.delete(projects);
  }
);
