/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users");

  const projects = new Collection({
    name: "projects",
    type: "base",
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
        maxSelect: 999999,
      }
    ],
    listRule: "",
    viewRule: "",
  });
  app.save(projects);

  const tasks = new Collection({
    name: "tasks",
    type: "base",
    fields: [
      {
        name: "title",
        type: "text",
        required: true,
      },
      {
        name: "project",
        type: "relation",
        collectionId: projects.id,
        maxSelect: 1,
      }
    ],
    listRule: "@request.auth.id ?= project.members",
    viewRule: "@request.auth.id ?= project.members",
  });
  app.save(tasks);
}, (app) => {
  const tasks = app.findCollectionByNameOrId("tasks");
  app.delete(tasks);
  const projects = app.findCollectionByNameOrId("projects");
  app.delete(projects);
});
