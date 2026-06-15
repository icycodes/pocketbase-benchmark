migrate((app) => {
  const users = app.findCollectionByNameOrId("users");

  const projects = new Collection({
    name: "projects",
    type: "base",
    listRule: "members ?= @request.auth.id",
    viewRule: "members ?= @request.auth.id",
    createRule: "@request.auth.id != ''",
    updateRule: "members ?= @request.auth.id",
    deleteRule: "members ?= @request.auth.id",
    fields: [
      {
        name: "name",
        type: "text",
        required: true
      },
      {
        name: "members",
        type: "relation",
        required: true,
        collectionId: users.id,
        cascadeDelete: false,
        maxSelect: 0
      }
    ]
  });
  app.save(projects);

  const tasks = new Collection({
    name: "tasks",
    type: "base",
    listRule: "project.members ?= @request.auth.id",
    viewRule: "project.members ?= @request.auth.id",
    createRule: "project.members ?= @request.auth.id",
    updateRule: "project.members ?= @request.auth.id",
    deleteRule: "project.members ?= @request.auth.id",
    fields: [
      {
        name: "title",
        type: "text",
        required: true
      },
      {
        name: "description",
        type: "text",
        required: false
      },
      {
        name: "project",
        type: "relation",
        required: true,
        collectionId: projects.id,
        cascadeDelete: false,
        maxSelect: 1
      }
    ]
  });
  app.save(tasks);

}, (app) => {
  try {
    const tasks = app.findCollectionByNameOrId("tasks");
    app.delete(tasks);
  } catch(e) {}
  try {
    const projects = app.findCollectionByNameOrId("projects");
    app.delete(projects);
  } catch(e) {}
});