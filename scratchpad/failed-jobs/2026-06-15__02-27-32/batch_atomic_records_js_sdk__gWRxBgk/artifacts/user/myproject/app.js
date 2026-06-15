#!/usr/bin/env node
// Atomic order + items creation using PocketBase JS SDK Batch API
'use strict';

const PocketBase = require('pocketbase/cjs');

// ── parse CLI args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);

function getFlag(name) {
  return args.includes(name);
}

function getFlagValue(name) {
  const idx = args.indexOf(name);
  if (idx === -1) return null;
  return args[idx + 1] ?? null;
}

const itemsArg = getFlagValue('--items');
const failMode = getFlag('--fail');

if (itemsArg === null || isNaN(Number(itemsArg)) || Number(itemsArg) < 1) {
  process.stderr.write('Usage: node app.js --items <N> [--fail]\n');
  process.exit(1);
}

const N = parseInt(itemsArg, 10);

// ── env vars ───────────────────────────────────────────────────────────────────
const PB_URL           = process.env.PB_URL;
const PB_ADMIN_EMAIL   = process.env.PB_ADMIN_EMAIL;
const PB_ADMIN_PASSWORD= process.env.PB_ADMIN_PASSWORD;
const ZEALT_RUN_ID     = process.env.ZEALT_RUN_ID;

if (!PB_URL || !PB_ADMIN_EMAIL || !PB_ADMIN_PASSWORD) {
  process.stderr.write('Missing required env vars: PB_URL, PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD\n');
  process.exit(1);
}

// ── generate a PocketBase-compatible 15-char lowercase alphanumeric id ─────────
function generateId() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let id = '';
  // ensure first char is a letter (to satisfy ^[a-z0-9]+$ and typical PB ids)
  for (let i = 0; i < 15; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

// ── main ───────────────────────────────────────────────────────────────────────
async function main() {
  const pb = new PocketBase(PB_URL);

  // authenticate as superuser / admin
  await pb.collection('_superusers').authWithPassword(PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD);

  // pre-generate the order id so order_items can reference it within the same batch
  const orderId = generateId();

  // build the batch
  const batch = pb.createBatch();

  // 1. create the order record (with explicit id)
  batch.collection('orders').create({
    id:       orderId,
    customer: ZEALT_RUN_ID,
    total:    0,
  });

  // 2. create N order_item records referencing the order
  for (let i = 0; i < N; i++) {
    batch.collection('order_items').create({
      order:    orderId,
      product:  `product-${i + 1}`,
      quantity: 1,
    });
  }

  // 3. in --fail mode, append one intentionally invalid record to force rollback
  //    quantity has min=1 and onlyInt=true; sending quantity=0 violates validation
  if (failMode) {
    batch.collection('order_items').create({
      order:    orderId,
      product:  'invalid-item-to-force-rollback',
      quantity: 0,          // violates min:1 → server rejects the whole batch
    });
  }

  // send the batch (atomic / transactional)
  try {
    await batch.send();
  } catch (err) {
    if (failMode) {
      process.stderr.write('BATCH_ROLLED_BACK\n');
      process.exit(1);
    }
    // unexpected error in normal mode
    process.stderr.write(`Batch failed: ${err.message}\n`);
    process.exit(1);
  }

  if (failMode) {
    // batch unexpectedly succeeded — shouldn't happen, but guard anyway
    process.stderr.write('ERROR: batch succeeded but --fail was requested\n');
    process.exit(1);
  }

  // success: print exactly one line matching ^ORDER:[a-z0-9]{15}$
  process.stdout.write(`ORDER:${orderId}\n`);
  process.exit(0);
}

main().catch((err) => {
  process.stderr.write(`Unhandled error: ${err.message}\n`);
  process.exit(1);
});
