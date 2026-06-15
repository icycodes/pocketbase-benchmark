#!/usr/bin/env node
'use strict';

// Polyfill EventSource for Node.js (the pocketbase SDK's realtime layer needs it)
import { EventSource } from 'eventsource';
globalThis.EventSource = EventSource;

import PocketBase from 'pocketbase';

// ---------------------------------------------------------------------------
// Parse --chat <chatId> from argv
// ---------------------------------------------------------------------------
function parseChatId() {
  const args = process.argv.slice(2);
  const idx = args.indexOf('--chat');
  if (idx === -1 || idx + 1 >= args.length) {
    process.stderr.write('Usage: node subscribe.js --chat <chatId>\n');
    process.exit(1);
  }
  return args[idx + 1];
}

// ---------------------------------------------------------------------------
// Write a single JSON event line to stdout
// ---------------------------------------------------------------------------
function emitEvent(action, record) {
  const line = JSON.stringify({ action, record }) + '\n';
  process.stdout.write(line);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const chatId = parseChatId();

  const pb = new PocketBase('http://127.0.0.1:8090');

  // Authenticate as superuser so the realtime subscription is authorised
  const email = process.env.PB_ADMIN_EMAIL;
  const password = process.env.PB_ADMIN_PASSWORD;

  if (!email || !password) {
    process.stderr.write('PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD env vars are required\n');
    process.exit(1);
  }

  // PocketBase >= 0.23: superusers live in the _superusers collection
  await pb.collection('_superusers').authWithPassword(email, password);

  // Subscribe to all records (*) in the messages collection.
  // The `filter` option is sent to PocketBase as a server-side constraint
  // so only events whose chat field equals chatId are delivered over SSE.
  const unsubscribe = await pb.collection('messages').subscribe(
    '*',
    (e) => {
      emitEvent(e.action, e.record);
    },
    {
      // Server-side filter – PocketBase evaluates this before sending the event
      filter: `chat = "${chatId.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`,
    }
  );

  process.stderr.write(`Subscribed to messages where chat="${chatId}"\n`);

  // ---------------------------------------------------------------------------
  // Graceful shutdown on SIGTERM: unsubscribe then exit 0
  // ---------------------------------------------------------------------------
  process.on('SIGTERM', async () => {
    process.stderr.write('SIGTERM received, unsubscribing…\n');
    try {
      await Promise.race([
        unsubscribe(),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000)),
      ]);
    } catch (_) {
      // ignore – proceed to exit anyway
    }
    process.exit(0);
  });
}

main().catch((err) => {
  process.stderr.write(`Fatal error: ${err.message ?? err}\n`);
  process.exit(1);
});
