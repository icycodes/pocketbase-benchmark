/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
  // Create the documents collection
  const documents = new Collection({
    name: "documents",
    type: "base",
    system: false,
    schema: [
      {
        name: "title",
        type: "text",
        required: false,
        system: false,
        options: {
          min: null,
          max: null,
          pattern: "",
        },
      },
      {
        name: "author",
        type: "relation",
        required: true,
        system: false,
        options: {
          collectionId: "systemprofiles0",
          cascadeDelete: false,
          minSelect: 1,
          maxSelect: 1,
          displayFields: [],
        },
      },
    ],
    listRule: "",
    viewRule: "",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {},
  });

  app.save(documents);

  // Create the document_edit_permissions collection
  const editPermissions = new Collection({
    name: "document_edit_permissions",
    type: "base",
    system: false,
    schema: [
      {
        name: "document",
        type: "relation",
        required: true,
        system: false,
        options: {
          collectionId: documents.id,
          cascadeDelete: false,
          minSelect: 1,
          maxSelect: 1,
          displayFields: [],
        },
      },
      {
        name: "grantee",
        type: "relation",
        required: true,
        system: false,
        options: {
          collectionId: "systemprofiles0",
          cascadeDelete: false,
          minSelect: 1,
          maxSelect: 1,
          displayFields: [],
        },
      },
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {},
  });

  app.save(editPermissions);
}, (app) => {
  const editPerms = app.findCollectionByNameOrId("document_edit_permissions");
  if (editPerms) {
    app.delete(editPerms);
  }
  const docs = app.findCollectionByNameOrId("documents");
  if (docs) {
    app.delete(docs);
  }
});
