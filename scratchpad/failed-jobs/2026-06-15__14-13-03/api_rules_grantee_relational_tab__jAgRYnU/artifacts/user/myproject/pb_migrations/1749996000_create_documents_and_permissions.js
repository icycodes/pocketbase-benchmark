/// <reference path="../pb_data/types.d.ts" />

migrate(
  (app) => {
    // Look up the real ID of the built-in users auth collection
    const usersCollection = app.findCollectionByNameOrId("users");

    // -------------------------------------------------------------------------
    // Step 1 – Create `documents` WITHOUT the update rule first.
    //          The back-relation rule references `document_edit_permissions`,
    //          which does not exist yet, so we add the rule after step 2.
    // -------------------------------------------------------------------------
    const documents = new Collection({
      name: "documents",
      type: "base",

      // Public read (empty string = anyone, including unauthenticated)
      listRule: "",
      viewRule: "",

      // Locked until we patch in step 3
      createRule: null,
      updateRule: null,
      deleteRule: null,

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
          collectionId: usersCollection.id,
          cascadeDelete: false,
          maxSelect: 1,
        },
      ],
    });

    app.save(documents);

    // -------------------------------------------------------------------------
    // Step 2 – Create `document_edit_permissions`.
    // -------------------------------------------------------------------------
    const permissions = new Collection({
      name: "document_edit_permissions",
      type: "base",

      // Fully locked; managed only via admin UI or server-side hooks
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,

      fields: [
        {
          name: "document",
          type: "relation",
          required: true,
          collectionId: documents.id,
          cascadeDelete: true, // remove permission rows when the document is deleted
          maxSelect: 1,
        },
        {
          name: "grantee",
          type: "relation",
          required: true,
          collectionId: usersCollection.id,
          cascadeDelete: false,
          maxSelect: 1,
        },
      ],
    });

    app.save(permissions);

    // -------------------------------------------------------------------------
    // Step 3 – Patch `documents` with the relational update rule.
    //
    //   Semantics:
    //     "@request.auth.id = author"
    //       → the requesting user IS the document's author, OR
    //
    //     "@request.auth.id ?= document_edit_permissions_via_document.grantee"
    //       → at least one document_edit_permissions row whose `document`
    //         field equals this document's id has `grantee` == auth user id
    // -------------------------------------------------------------------------
    const docsCollection = app.findCollectionByNameOrId("documents");
    docsCollection.updateRule =
      "@request.auth.id = author || @request.auth.id ?= document_edit_permissions_via_document.grantee";
    app.save(docsCollection);
  },

  // down – revert the migration
  (app) => {
    for (const name of ["document_edit_permissions", "documents"]) {
      try {
        app.delete(app.findCollectionByNameOrId(name));
      } catch (_) {}
    }
  }
);
