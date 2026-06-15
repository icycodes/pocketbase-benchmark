migrate((app) => {
  // Create organizations collection
  const organizations = new Collection({
    name: "organizations",
    type: "base",
    fields: [
      {
        type: "text",
        name: "name"
      }
    ]
  });
  app.dao().saveCollection(organizations);

  // Find the built-in users collection for reference
  const users = app.dao().findCollectionByNameOrId("users");

  // Create organization_members collection
  const organizationMembers = new Collection({
    name: "organization_members",
    type: "base",
    fields: [
      {
        type: "relation",
        name: "user",
        collectionId: users.id,
        maxSelect: 1
      },
      {
        type: "relation",
        name: "organization",
        collectionId: organizations.id,
        maxSelect: 1
      },
      {
        type: "select",
        name: "role",
        maxSelect: 1,
        values: ["owner", "editor", "viewer"]
      }
    ]
  });
  app.dao().saveCollection(organizationMembers);

  // Create documents collection with role-based API rules
  const documents = new Collection({
    name: "documents",
    type: "base",
    fields: [
      {
        type: "text",
        name: "title"
      },
      {
        type: "text",
        name: "content"
      },
      {
        type: "relation",
        name: "organization",
        collectionId: organizations.id,
        maxSelect: 1
      }
    ],
    listRule: "@collection.organization_members.user = @request.auth.id && @collection.organization_members.organization = organization",
    viewRule: "@collection.organization_members.user = @request.auth.id && @collection.organization_members.organization = organization",
    createRule: "@collection.organization_members.user = @request.auth.id && @collection.organization_members.organization = @request.body.organization && (@collection.organization_members.role = 'owner' || @collection.organization_members.role = 'editor')",
    updateRule: "@collection.organization_members.user = @request.auth.id && @collection.organization_members.organization = organization && (@collection.organization_members.role = 'owner' || @collection.organization_members.role = 'editor')",
    deleteRule: "@collection.organization_members.user = @request.auth.id && @collection.organization_members.organization = organization && @collection.organization_members.role = 'owner'"
  });
  app.dao().saveCollection(documents);
}, (app) => {
  // Down migration - delete in reverse order
  app.dao().deleteCollection(app.dao().findCollectionByNameOrId("documents"));
  app.dao().deleteCollection(app.dao().findCollectionByNameOrId("organization_members"));
  app.dao().deleteCollection(app.dao().findCollectionByNameOrId("organizations"));
});