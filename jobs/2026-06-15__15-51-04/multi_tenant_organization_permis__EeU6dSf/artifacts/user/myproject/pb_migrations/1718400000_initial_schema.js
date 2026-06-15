/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
  // 1. Create organizations collection
  const organizations = new Collection({
    name: "organizations",
    type: "base",
    system: false,
    schema: [
      {
        name: "name",
        type: "text",
        required: true,
        options: {
          min: 1,
          max: 255,
          pattern: "",
        },
      },
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    indexes: [],
  });

  app.save(organizations);

  // 2. Create organization_members collection
  const organizationMembers = new Collection({
    name: "organization_members",
    type: "base",
    system: false,
    schema: [
      {
        name: "member",
        type: "relation",
        required: true,
        options: {
          collectionId: "users",
          cascadeDelete: false,
          maxSelect: 1,
          minSelect: 1,
        },
      },
      {
        name: "organization",
        type: "relation",
        required: true,
        options: {
          collectionId: organizations.id,
          cascadeDelete: true,
          maxSelect: 1,
          minSelect: 1,
        },
      },
      {
        name: "role",
        type: "select",
        required: true,
        options: {
          maxSelect: 1,
          values: ["owner", "editor", "viewer"],
        },
      },
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    indexes: [],
  });

  app.save(organizationMembers);

  // 3. Create documents collection with API rules
  const documents = new Collection({
    name: "documents",
    type: "base",
    system: false,
    schema: [
      {
        name: "title",
        type: "text",
        required: true,
        options: {
          min: 1,
          max: 255,
          pattern: "",
        },
      },
      {
        name: "content",
        type: "text",
        required: false,
        options: {
          min: null,
          max: null,
          pattern: "",
        },
      },
      {
        name: "organization",
        type: "relation",
        required: true,
        options: {
          collectionId: organizations.id,
          cascadeDelete: true,
          maxSelect: 1,
          minSelect: 1,
        },
      },
    ],
    listRule:
      "@collection.organization_members.member = @request.auth.id && @collection.organization_members.organization = organization",
    viewRule:
      "@collection.organization_members.member = @request.auth.id && @collection.organization_members.organization = organization",
    createRule:
      "@request.auth.id != '' && @collection.organization_members.member = @request.auth.id && @collection.organization_members.organization = @request.body.organization && (@collection.organization_members.role = 'owner' || @collection.organization_members.role = 'editor')",
    updateRule:
      "@request.auth.id != '' && @collection.organization_members.member = @request.auth.id && @collection.organization_members.organization = organization && (@collection.organization_members.role = 'owner' || @collection.organization_members.role = 'editor')",
    deleteRule:
      "@request.auth.id != '' && @collection.organization_members.member = @request.auth.id && @collection.organization_members.organization = organization && @collection.organization_members.role = 'owner'",
    indexes: [],
  });

  app.saveNoValidate(documents);
});
