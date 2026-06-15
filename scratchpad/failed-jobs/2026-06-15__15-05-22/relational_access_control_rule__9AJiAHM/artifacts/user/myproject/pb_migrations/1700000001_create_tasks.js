migrate((app) => {
  const projectsCollection = app.findCollectionByNameOrId("projects");

  const collection = new Collection({
    name: "tasks",
    type: "base",
    fields: [
      {
        system: false,
        id: "titleText1234567",
        name: "title",
        type: "text",
        required: false,
        options: {
          min: null,
          max: null,
          pattern: ""
        }
      },
      {
        system: false,
        id: "projectRel123456",
        name: "project",
        type: "relation",
        required: false,
        options: {
          collectionId: projectsCollection.id,
          cascadeDelete: false,
          minSelect: null,
          maxSelect: 1,
          displayFields: ["id"]
        }
      }
    ],
    indexes: [],
    listRule: "@request.auth.id ?= project.members",
    viewRule: "@request.auth.id ?= project.members",
    createRule: null,
    updateRule: null,
    deleteRule: null
  });

  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("tasks");
  app.delete(collection);
});