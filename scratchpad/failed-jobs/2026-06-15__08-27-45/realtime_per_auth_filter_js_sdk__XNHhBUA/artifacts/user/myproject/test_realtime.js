// Polyfill EventSource for Node.js (needed by PocketBase SDK for SSE)
global.EventSource = require("eventsource").EventSource;

const PocketBase = require("pocketbase/cjs");

const PB_URL = "http://127.0.0.1:8090";
const ADMIN_EMAIL = "admin@test.com";
const ADMIN_PASSWORD = "test123456";

const USER_A_EMAIL = "usera@test.com";
const USER_A_PASSWORD = "userapass123";
const USER_B_EMAIL = "userb@test.com";
const USER_B_PASSWORD = "userbpass123";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  // ---------- Step 1: Admin client for setup ----------
  const adminPb = new PocketBase(PB_URL);
  await adminPb
    .collection("_superusers")
    .authWithPassword(ADMIN_EMAIL, ADMIN_PASSWORD);
  console.log("Admin authenticated.");

  // ---------- Step 2: Get the users collection ID ----------
  const usersCollection = await adminPb.collections.getFirstListItem(
    'name = "users"'
  );
  const usersCollectionId = usersCollection.id;
  console.log(`Users collection id: ${usersCollectionId}`);

  // ---------- Step 3: Create the "messages" collection ----------
  // Clean up if exists from a previous run
  try {
    const existing = await adminPb.collections.getFirstListItem(
      'name = "messages"'
    );
    await adminPb.collections.delete(existing.id);
    console.log("Deleted existing 'messages' collection.");
  } catch (_) {
    // doesn't exist, that's fine
  }

  const messagesCollection = await adminPb.collections.create({
    name: "messages",
    type: "base",
    listRule: "user = @request.auth.id",
    viewRule: "user = @request.auth.id",
    createRule: "",
    updateRule: "",
    deleteRule: "",
    fields: [
      {
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1,
      },
    ],
  });
  console.log("Created 'messages' collection.");

  // ---------- Step 4: Create User A and User B ----------
  let userA, userB;

  // Clean up existing test users if any
  try {
    const existingA = await adminPb
      .collection("users")
      .getFirstListItem(`email = "${USER_A_EMAIL}"`);
    await adminPb.collection("users").delete(existingA.id);
  } catch (_) {}
  try {
    const existingB = await adminPb
      .collection("users")
      .getFirstListItem(`email = "${USER_B_EMAIL}"`);
    await adminPb.collection("users").delete(existingB.id);
  } catch (_) {}

  const createdA = await adminPb.collection("users").create({
    email: USER_A_EMAIL,
    password: USER_A_PASSWORD,
    passwordConfirm: USER_A_PASSWORD,
  });
  userA = createdA;
  console.log(`Created User A (id: ${userA.id}).`);

  const createdB = await adminPb.collection("users").create({
    email: USER_B_EMAIL,
    password: USER_B_PASSWORD,
    passwordConfirm: USER_B_PASSWORD,
  });
  userB = createdB;
  console.log(`Created User B (id: ${userB.id}).`);

  // ---------- Step 5: Subscribe as User A ----------
  const userAPb = new PocketBase(PB_URL);
  await userAPb
    .collection("users")
    .authWithPassword(USER_A_EMAIL, USER_A_PASSWORD);
  console.log("User A authenticated.");

  const receivedEvents = [];

  await userAPb.collection("messages").subscribe("*", (data) => {
    console.log(
      `User A received event: action=${data.action}, record.id=${data.record.id}, record.user=${data.record.user}`
    );
    receivedEvents.push(data);
  });

  // Give the SSE subscription a moment to establish
  await sleep(500);

  // ---------- Step 6: Create messages (as admin) ----------
  // Create a message assigned to User A
  const msgA = await adminPb.collection("messages").create({
    user: userA.id,
  });
  console.log(`Created message for User A (id: ${msgA.id}).`);

  // Small delay between creates
  await sleep(200);

  // Create a message assigned to User B
  const msgB = await adminPb.collection("messages").create({
    user: userB.id,
  });
  console.log(`Created message for User B (id: ${msgB.id}).`);

  // ---------- Step 7: Wait for SSE events to arrive ----------
  await sleep(2000);

  // Unsubscribe
  await userAPb.collection("messages").unsubscribe();
  await sleep(300);

  // ---------- Step 8: Assertions ----------
  console.log(`\nTotal events received: ${receivedEvents.length}`);

  // User A should have received exactly 1 event (their own message)
  if (receivedEvents.length !== 1) {
    console.error(
      `FAIL: Expected 1 event, but got ${receivedEvents.length}`
    );
    for (const ev of receivedEvents) {
      console.error(
        `  - action=${ev.action}, record.id=${ev.record.id}, record.user=${ev.record.user}`
      );
    }
    process.exit(1);
  }

  const event = receivedEvents[0];

  // The event should be for User A's message
  if (event.action !== "create") {
    console.error(`FAIL: Expected action "create", got "${event.action}"`);
    process.exit(1);
  }

  if (event.record.id !== msgA.id) {
    console.error(
      `FAIL: Expected record.id "${msgA.id}", got "${event.record.id}"`
    );
    process.exit(1);
  }

  if (event.record.user !== userA.id) {
    console.error(
      `FAIL: Expected record.user "${userA.id}", got "${event.record.user}"`
    );
    process.exit(1);
  }

  console.log("Test passed!");
  process.exit(0);
}

main().catch((err) => {
  console.error("Test failed with error:", err?.message || err);
  if (err?.response) {
    console.error("Response data:", JSON.stringify(err.response, null, 2));
  }
  process.exit(1);
});
