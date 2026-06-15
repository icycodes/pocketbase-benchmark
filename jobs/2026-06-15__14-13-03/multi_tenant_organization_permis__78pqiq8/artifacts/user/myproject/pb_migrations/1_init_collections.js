/// <reference path="../pb_data/types.d.ts" />

migrate(
  (app) => {
    // -------------------------------------------------------------------------
    // 1. organizations collection
    // -------------------------------------------------------------------------
    const organizations = new Collection({
      type: "base",
      name: "organizations",
      fields: [
        {
          type: "text",
          name: "name",
          required: true,
        },
      ],
      // No special API rules — managed by admins / adjust as needed
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
    });
    app.save(organizations);

    // -------------------------------------------------------------------------
    // 2. organization_members collection
    // -------------------------------------------------------------------------
    const organizationMembers = new Collection({
      type: "base",
      name: "organization_members",
      fields: [
        {
          type: "relation",
          name: "user",
          required: true,
          collectionId: "_pb_users_auth_",
          cascadeDelete: true,
          maxSelect: 1,
        },
        {
          type: "relation",
          name: "organization",
          required: true,
          collectionId: organizations.id,
          cascadeDelete: true,
          maxSelect: 1,
        },
        {
          type: "select",
          name: "role",
          required: true,
          maxSelect: 1,
          values: ["owner", "editor", "viewer"],
        },
      ],
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
    });
    app.save(organizationMembers);

    // -------------------------------------------------------------------------
    // 3. documents collection  (with RBAC API rules)
    // -------------------------------------------------------------------------
    //
    // Rule syntax reference:
    //   @collection.<name>.<field> — sub-query against another collection
    //   @request.auth.id           — the authenticated user's ID
    //   @request.body.<field>      — value supplied in the request body
    //
    // List / View:
    //   The requesting user must have ANY membership record for the document's
    //   organization (role is irrelevant).
    //
    // Create:
    //   The requesting user must be an owner OR editor in the organization they
    //   are assigning the new document to (@request.body.organization).
    //
    // Update:
    //   The requesting user must be an owner OR editor in the document's
    //   existing organization field.
    //
    // Delete:
    //   The requesting user must be an owner in the document's organization.
    // -------------------------------------------------------------------------

    const listViewRule =
      "@collection.organization_members.user.id ?= @request.auth.id &&" +
      " @collection.organization_members.organization.id ?= organization";

    const createRule =
      "@collection.organization_members.user.id ?= @request.auth.id &&" +
      " @collection.organization_members.organization.id ?= @request.body.organization &&" +
      " (@collection.organization_members.role ?= 'owner' ||" +
      "  @collection.organization_members.role ?= 'editor')";

    const updateRule =
      "@collection.organization_members.user.id ?= @request.auth.id &&" +
      " @collection.organization_members.organization.id ?= organization &&" +
      " (@collection.organization_members.role ?= 'owner' ||" +
      "  @collection.organization_members.role ?= 'editor')";

    const deleteRule =
      "@collection.organization_members.user.id ?= @request.auth.id &&" +
      " @collection.organization_members.organization.id ?= organization &&" +
      " @collection.organization_members.role ?= 'owner'";

    const documents = new Collection({
      type: "base",
      name: "documents",
      fields: [
        {
          type: "text",
          name: "title",
          required: true,
        },
        {
          type: "text",
          name: "content",
        },
        {
          type: "relation",
          name: "organization",
          required: true,
          collectionId: organizations.id,
          cascadeDelete: true,
          maxSelect: 1,
        },
      ],
      listRule: listViewRule,
      viewRule: listViewRule,
      createRule: createRule,
      updateRule: updateRule,
      deleteRule: deleteRule,
    });
    app.save(documents);
  },

  // Down migration — drop all three collections in reverse dependency order
  (app) => {
    for (const name of ["documents", "organization_members", "organizations"]) {
      try {
        const col = app.findCollectionByNameOrId(name);
        app.delete(col);
      } catch (_) {
        // already gone
      }
    }
  }
);
