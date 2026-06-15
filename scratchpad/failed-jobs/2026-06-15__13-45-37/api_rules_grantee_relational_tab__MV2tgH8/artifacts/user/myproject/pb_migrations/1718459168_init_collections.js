migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users");

  // Step 1: Create documents collection with temporary update rule
  const documents = new Collection({
    name: "documents",
    type: "base",
    listRule: "",
    viewRule: "",
    createRule: "@request.auth.id != ''",
    updateRule: "@request.auth.id != ''", // Temporary rule until permissions collection exists
    deleteRule: "@request.auth.id != '' && author = @request.auth.id",
    fields: [
      {
        name: "title",
        type: "text",
        required: false,
      },
      {
        name: "author",
        type: "relation",
        required: true,
        maxSelect: 1,
        collectionId: usersCollection.id,
        cascadeDelete: true,
      }
    ]
  });

  app.save(documents);

  // Step 2: Create document_edit_permissions collection
  const permissions = new Collection({
    name: "document_edit_permissions",
    type: "base",
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: "@request.auth.id != ''",
    deleteRule: "@request.auth.id != ''",
    fields: [
      {
        name: "document",
        type: "relation",
        required: true,
        maxSelect: 1,
        collectionId: documents.id,
        cascadeDelete: true,
      },
      {
        name: "grantee",
        type: "relation",
        required: true,
        maxSelect: 1,
        collectionId: usersCollection.id,
        cascadeDelete: true,
      }
    ]
  });

  app.save(permissions);

  // Step 3: Update documents collection with the final update rule referencing the back-relation
  const savedDocuments = app.findCollectionByNameOrId("documents");
  savedDocuments.updateRule = "@request.auth.id != '' && (author = @request.auth.id || document_edit_permissions_via_document.grantee ?= @request.auth.id)";
  app.save(savedDocuments);

}, (app) => {
  try {
    const permissions = app.findCollectionByNameOrId("document_edit_permissions");
    app.delete(permissions);
  } catch (e) {}

  try {
    const documents = app.findCollectionByNameOrId("documents");
    app.delete(documents);
  } catch (e) {}
});
