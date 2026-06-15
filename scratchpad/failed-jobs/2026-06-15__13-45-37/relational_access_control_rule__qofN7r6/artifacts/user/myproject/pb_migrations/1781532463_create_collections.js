/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users");
  const usersCollectionId = usersCollection.id;

  const projectsCollection = new Collection({
    type: "base",
    name: "projects",
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: "@request.auth.id != ''",
    deleteRule: "@request.auth.id != ''",
    fields: [
      {
        name: "name",
        type: "text",
        required: true,
      },
      {
        name: "members",
        type: "relation",
        required: false,
        maxSelect: 999,
        collectionId: usersCollectionId,
        cascadeDelete: false,
      }
    ]
  });

  app.save(projectsCollection);

  const savedProjects = app.findCollectionByNameOrId("projects");
  const projectsCollectionId = savedProjects.id;

  const tasksCollection = new Collection({
    type: "base",
    name: "tasks",
    listRule: "@request.auth.id ?= project.members.id",
    viewRule: "@request.auth.id ?= project.members.id",
    createRule: "@request.auth.id != ''",
    updateRule: "@request.auth.id != ''",
    deleteRule: "@request.auth.id != ''",
    fields: [
      {
        name: "title",
        type: "text",
        required: true,
      },
      {
        name: "project",
        type: "relation",
        required: true,
        maxSelect: 1,
        collectionId: projectsCollectionId,
        cascadeDelete: true,
      }
    ]
  });

  app.save(tasksCollection);
}, (app) => {
  try {
    const tasks = app.findCollectionByNameOrId("tasks");
    app.dao().deleteCollection(tasks);
  } catch (e) {}
  try {
    const projects = app.findCollectionByNameOrId("projects");
    app.dao().deleteCollection(projects);
  } catch (e) {}
})
