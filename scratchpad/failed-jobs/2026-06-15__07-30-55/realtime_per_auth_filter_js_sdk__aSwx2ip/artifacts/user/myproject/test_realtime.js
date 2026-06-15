/**
 * test_realtime.js
 *
 * Tests PocketBase's per-auth realtime filter behavior:
 * - Subscribes to the `messages` collection as User A.
 * - Creates a message owned by User A and one owned by User B.
 * - Asserts that only the User A message event is received by User A's subscription.
 */

"use strict";

// Polyfill EventSource for Node.js (the PocketBase SDK's RealtimeService requires it).
// The `eventsource` package (v3+) uses named exports: { EventSource }.
const { EventSource } = require("eventsource");
global.EventSource = EventSource;

const PocketBase = require("pocketbase/cjs");

const PB_URL = "http://127.0.0.1:8090";
const ADMIN_EMAIL = "admin@example.com";
const ADMIN_PASSWORD = "admin123456";

// ── helpers ──────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Return a fresh, independent PocketBase client.
 * Using separate instances per actor avoids shared auth-store state.
 */
function makeClient() {
  return new PocketBase(PB_URL);
}

// ── main ─────────────────────────────────────────────────────────────────────

async function main() {
  // ── 1. Admin client ────────────────────────────────────────────────────────
  const adminPb = makeClient();
  await adminPb.collection("_superusers").authWithPassword(
    ADMIN_EMAIL,
    ADMIN_PASSWORD
  );
  console.log("[setup] Admin authenticated.");

  // ── 2. Tear down any previous test state ───────────────────────────────────
  // Delete the `messages` collection if it already exists so every run is clean.
  try {
    const existing = await adminPb.collections.getOne("messages");
    if (existing) {
      await adminPb.collections.delete("messages");
      console.log("[setup] Removed existing 'messages' collection.");
    }
  } catch (_) {
    // Not found — that's fine.
  }

  // Delete leftover test users.
  for (const email of ["usera@example.com", "userb@example.com"]) {
    try {
      const u = await adminPb
        .collection("users")
        .getFirstListItem(`email='${email}'`);
      await adminPb.collection("users").delete(u.id);
    } catch (_) {
      // Not found — ignore.
    }
  }

  // ── 3. Create the `messages` collection with a user relation + ListRule ────
  const usersCollection = await adminPb.collections.getOne("users");

  await adminPb.collections.create({
    name: "messages",
    type: "base",
    // Only show events for records where the `user` field matches the
    // authenticated user — this is the rule under test.
    listRule: "user = @request.auth.id",
    viewRule: "user = @request.auth.id",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null,
    fields: [
      {
        type: "relation",
        name: "user",
        required: true,
        collectionId: usersCollection.id,
        cascadeDelete: false,
        maxSelect: 1,
      },
    ],
  });
  console.log("[setup] 'messages' collection created.");

  // ── 4. Create User A and User B ────────────────────────────────────────────
  const password = "Password123!";

  const userA = await adminPb.collection("users").create({
    email: "usera@example.com",
    password,
    passwordConfirm: password,
    emailVisibility: true,
    verified: true,
  });
  console.log("[setup] User A created:", userA.id);

  const userB = await adminPb.collection("users").create({
    email: "userb@example.com",
    password,
    passwordConfirm: password,
    emailVisibility: true,
    verified: true,
  });
  console.log("[setup] User B created:", userB.id);

  // ── 5. Authenticate as User A and subscribe to `messages` ─────────────────
  const pbA = makeClient();
  await pbA.collection("users").authWithPassword("usera@example.com", password);
  console.log("[test]  User A authenticated.");

  const receivedRecordIds = [];

  const unsubscribe = await pbA.collection("messages").subscribe("*", (e) => {
    console.log(`[event] Received SSE action='${e.action}' record.id='${e.record?.id}'`);
    receivedRecordIds.push(e.record?.id);
  });
  console.log("[test]  User A subscribed to 'messages'.");

  // Give the SSE connection a moment to fully establish.
  await sleep(800);

  // ── 6. Create messages via admin (bypasses ListRule on write side) ─────────
  const msgA = await adminPb.collection("messages").create({ user: userA.id });
  console.log("[test]  Message for User A created:", msgA.id);

  const msgB = await adminPb.collection("messages").create({ user: userB.id });
  console.log("[test]  Message for User B created:", msgB.id);

  // Wait long enough for SSE events to propagate to the client.
  await sleep(1500);

  // ── 7. Unsubscribe and evaluate ────────────────────────────────────────────
  await unsubscribe();

  console.log("[test]  Events received for record IDs:", receivedRecordIds);

  const receivedMsgA = receivedRecordIds.includes(msgA.id);
  const receivedMsgB = receivedRecordIds.includes(msgB.id);

  if (!receivedMsgA) {
    console.error(
      `FAIL: Expected to receive event for User A's message (${msgA.id}), but did not.`
    );
    process.exit(1);
  }

  if (receivedMsgB) {
    console.error(
      `FAIL: Received event for User B's message (${msgB.id}), but should NOT have.`
    );
    process.exit(1);
  }

  console.log("Test passed!");
  process.exit(0);
}

main().catch((err) => {
  console.error("Unhandled error:", err);
  process.exit(1);
});
