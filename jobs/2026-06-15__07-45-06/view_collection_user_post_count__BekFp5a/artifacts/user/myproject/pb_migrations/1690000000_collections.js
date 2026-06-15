migrate((db) => {
  const dao = new Dao(db);

  const posts = new Collection({
    id: "posts0000000000",
    name: "posts",
    type: "base",
    system: false,
    schema: [
      {
        id: "author00000000",
        name: "author",
        type: "relation",
        required: true,
        options: {
          collectionId: "_pb_users_auth_",
          cascadeDelete: false,
          minSelect: null,
          maxSelect: 1,
          displayFields: null
        }
      }
    ],
    listRule: "",
    viewRule: "",
    createRule: "",
    updateRule: "",
    deleteRule: "",
    options: {}
  });

  dao.saveCollection(posts);

  const userPostCounts = new Collection({
    id: "userpostcounts0",
    name: "user_post_counts",
    type: "view",
    system: false,
    schema: [
      {
        id: "username0000000",
        name: "username",
        type: "text",
        required: false,
        options: {
          min: null,
          max: null,
          pattern: ""
        }
      },
      {
        id: "postcount000000",
        name: "post_count",
        type: "number",
        required: false,
        options: {
          min: null,
          max: null,
          noDecimal: false
        }
      }
    ],
    listRule: "",
    viewRule: "",
    options: {
      query: "SELECT users.id, users.username, COUNT(posts.id) as post_count FROM users LEFT JOIN posts ON posts.author = users.id GROUP BY users.id"
    }
  });

  dao.saveCollection(userPostCounts);
}, (db) => {
  const dao = new Dao(db);
  
  try {
    const userPostCounts = dao.findCollectionByNameOrId("user_post_counts");
    dao.deleteCollection(userPostCounts);
  } catch (e) {}

  try {
    const posts = dao.findCollectionByNameOrId("posts");
    dao.deleteCollection(posts);
  } catch (e) {}
});