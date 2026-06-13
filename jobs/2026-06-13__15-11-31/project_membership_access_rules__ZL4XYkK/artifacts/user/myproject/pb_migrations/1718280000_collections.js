migrate((app) => {
  // 1. Resolve users collection
  const usersCollection = app.findCollectionByNameOrId("users");

  // 2. Create projects collection
  const projects = new Collection({
    name: "projects",
    type: "base",
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
        maxSelect: 999999, // multi-select with no upper bound
      }
    ]
  });

  // 3. Save projects collection
  app.save(projects);

  // 4. Resolve saved projects collection ID
  const projectsId = projects.id || app.findCollectionByNameOrId("projects").id;

  // 5. Create tasks collection
  const tasks = new Collection({
    name: "tasks",
    type: "base",
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
        collectionId: projectsId,
        maxSelect: 1, // single-relation
      }
    ]
  });

  // 6. Save tasks collection
  app.save(tasks);
}, (app) => {
  // Down/rollback migration
  try {
    const tasks = app.findCollectionByNameOrId("tasks");
    if (tasks) {
      app.delete(tasks);
    }
  } catch (e) {}

  try {
    const projects = app.findCollectionByNameOrId("projects");
    if (projects) {
      app.delete(projects);
    }
  } catch (e) {}
});
