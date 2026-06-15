migrate((app) => {
  // 1. Create organizations collection
  const organizations = new Collection({
    name: "organizations",
    type: "base",
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
      }
    ]
  });
  app.save(organizations);

  // 2. Create organization_members collection
  const organizationMembers = new Collection({
    name: "organization_members",
    type: "base",
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: "@request.auth.id != ''",
    deleteRule: "@request.auth.id != ''",
    fields: [
      {
        name: "user",
        type: "relation",
        required: true,
        collectionId: app.findCollectionByNameOrId("users").id,
        maxSelect: 1,
        cascadeDelete: true,
      },
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: app.findCollectionByNameOrId("organizations").id,
        maxSelect: 1,
        cascadeDelete: true,
      },
      {
        name: "role",
        type: "select",
        required: true,
        values: ["owner", "editor", "viewer"],
        maxSelect: 1,
      }
    ]
  });
  app.save(organizationMembers);

  // 3. Create documents collection
  const documents = new Collection({
    name: "documents",
    type: "base",
    listRule: "@request.auth.id != '' && @collection.organization_members.user ?= @request.auth.id && @collection.organization_members.organization ?= organization",
    viewRule: "@request.auth.id != '' && @collection.organization_members.user ?= @request.auth.id && @collection.organization_members.organization ?= organization",
    createRule: "@request.auth.id != '' && @collection.organization_members.user ?= @request.auth.id && @collection.organization_members.organization ?= @request.body.organization && (@collection.organization_members.role ?= 'owner' || @collection.organization_members.role ?= 'editor')",
    updateRule: "@request.auth.id != '' && @collection.organization_members.user ?= @request.auth.id && @collection.organization_members.organization ?= organization && (@collection.organization_members.role ?= 'owner' || @collection.organization_members.role ?= 'editor')",
    deleteRule: "@request.auth.id != '' && @collection.organization_members.user ?= @request.auth.id && @collection.organization_members.organization ?= organization && @collection.organization_members.role ?= 'owner'",
    fields: [
      {
        name: "title",
        type: "text",
        required: true,
      },
      {
        name: "content",
        type: "text",
        required: true,
      },
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: app.findCollectionByNameOrId("organizations").id,
        maxSelect: 1,
        cascadeDelete: true,
      }
    ]
  });
  app.save(documents);
}, (app) => {
  // Down migration
  try {
    const documents = app.findCollectionByNameOrId("documents");
    if (documents) app.delete(documents);
  } catch(e) {}

  try {
    const organizationMembers = app.findCollectionByNameOrId("organization_members");
    if (organizationMembers) app.delete(organizationMembers);
  } catch(e) {}

  try {
    const organizations = app.findCollectionByNameOrId("organizations");
    if (organizations) app.delete(organizations);
  } catch(e) {}
});
