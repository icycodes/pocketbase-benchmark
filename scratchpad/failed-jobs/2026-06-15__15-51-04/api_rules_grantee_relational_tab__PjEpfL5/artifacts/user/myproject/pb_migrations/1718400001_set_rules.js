/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
  const documents = app.findCollectionByNameOrId("documents");

  console.log("documents.fields:", JSON.stringify(documents.fields.map(f => ({ id: f.id, name: f.name, type: f.type }))));

  documents.updateRule = "@request.auth.id != '' && (@request.auth.id = author || id.document_edit_permissions_via_document.grantee ?= @request.auth.id)";
  app.save(documents);
}, (app) => {
  const documents = app.findCollectionByNameOrId("documents");
  documents.updateRule = null;
  app.save(documents);
});
