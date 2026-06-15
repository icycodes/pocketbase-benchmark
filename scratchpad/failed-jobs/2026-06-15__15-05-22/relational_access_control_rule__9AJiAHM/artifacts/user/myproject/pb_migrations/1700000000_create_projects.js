migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users");

  const collection = new Collection({
    name: "projects",
    type: "base",
    fields: [
      {
        system: false,
        id: "nameText1234567",
        name: "name",
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
        id: "membersRel123456",
        name: "members",
        type: "relation",
        required: false,
        options: {
          collectionId: usersCollection.id,
          cascadeDelete: false,
          minSelect: null,
          maxSelect: 0,
          displayFields: ["id"]
        }
      }
    ],
    indexes: [],
    listRule: "@request.auth.id ?= members",
    viewRule: "@request.auth.id ?= members",
    createRule: null,
    updateRule: null,
    deleteRule: null
  });

  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("projects");
  app.delete(collection);
});