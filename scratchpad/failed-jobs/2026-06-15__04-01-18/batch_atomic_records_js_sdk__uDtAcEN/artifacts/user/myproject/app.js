const PocketBase = require("pocketbase/cjs");

function generateId() {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let id = "";
  for (let i = 0; i < 15; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

async function main() {
  const args = process.argv.slice(2);

  // Parse --items <N> and --fail flags
  let itemsN = null;
  let failMode = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--items" && i + 1 < args.length) {
      itemsN = parseInt(args[i + 1], 10);
      i++;
    } else if (args[i] === "--fail") {
      failMode = true;
    }
  }

  if (itemsN === null || isNaN(itemsN) || itemsN < 0) {
    console.error("Usage: node app.js --items <N> [--fail]");
    process.exit(2);
  }

  const pbUrl = process.env.PB_URL;
  const pbAdminEmail = process.env.PB_ADMIN_EMAIL;
  const pbAdminPassword = process.env.PB_ADMIN_PASSWORD;
  const zealtRunId = process.env.ZEALT_RUN_ID;

  if (!pbUrl || !pbAdminEmail || !pbAdminPassword || !zealtRunId) {
    console.error("Missing required environment variables: PB_URL, PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD, ZEALT_RUN_ID");
    process.exit(2);
  }

  const pb = new PocketBase(pbUrl);

  // Authenticate as admin
  await pb.collection("_superusers").authWithPassword(pbAdminEmail, pbAdminPassword);

  // Pre-generate the order ID so we can reference it within the batch
  const orderId = generateId();

  const batch = pb.createBatch();

  // Create the order record with the pre-generated ID
  batch.collection("orders").create({
    id: orderId,
    customer: zealtRunId,
  });

  // Create N order_items, each referencing the order being created in the same batch
  for (let i = 0; i < itemsN; i++) {
    batch.collection("order_items").create({
      order: orderId,
      product: "item-" + (i + 1),
      quantity: 1,
    });
  }

  // In --fail mode, add a request that will cause the entire batch to fail.
  // We create an order_item referencing a deliberately invalid (non-existent) order ID.
  // This triggers a relation validation error server-side, rolling back the entire batch.
  if (failMode) {
    batch.collection("order_items").create({
      order: "nonexistent00000",
      product: "fail-item",
      quantity: 1,
    });
  }

  try {
    await batch.send();

    if (failMode) {
      // Should not reach here — the batch should have failed and been rolled back
      console.error("BATCH_ROLLED_BACK");
      process.exit(1);
    }

    console.log(`ORDER:${orderId}`);
    process.exit(0);
  } catch (err) {
    if (failMode) {
      console.error("BATCH_ROLLED_BACK");
      process.exit(1);
    }
    console.error("Batch request failed:", err.message);
    process.exit(1);
  }
}

main();
