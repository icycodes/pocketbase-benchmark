import PocketBase from 'pocketbase';

// Parse --chat <chatId> from command line
const chatIdx = process.argv.indexOf('--chat');
if (chatIdx === -1 || chatIdx + 1 >= process.argv.length) {
  console.error('Usage: node subscribe.js --chat <chatId>');
  process.exit(1);
}
const chatId = process.argv[chatIdx + 1];

const PB_URL = 'http://127.0.0.1:8090';
const PB_ADMIN_EMAIL = process.env.PB_ADMIN_EMAIL;
const PB_ADMIN_PASSWORD = process.env.PB_ADMIN_PASSWORD;

if (!PB_ADMIN_EMAIL || !PB_ADMIN_PASSWORD) {
  console.error('Error: PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD env vars must be set');
  process.exit(1);
}

const pb = new PocketBase(PB_URL);

let subscribed = false;

async function main() {
  // Authenticate as superuser so we can receive all events
  await pb.collection('_superusers').authWithPassword(PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD);

  // Subscribe to the messages collection with server-side filtering on the chat field.
  // The filter is passed as part of the options object, which the SDK serializes
  // into the subscription topic as query parameters for server-side filtering.
  await pb.collection('messages').subscribe('*', (e) => {
    // Only emit to stdout — the server-side filter ensures only matching records arrive.
    const output = JSON.stringify({ action: e.action, record: e.record });
    process.stdout.write(output + '\n');
  }, {
    filter: pb.filter('chat = {:chat}', { chat: chatId }),
  });

  subscribed = true;
}

// Graceful shutdown on SIGTERM: exit with code 0 within 3 seconds
let exiting = false;
process.on('SIGTERM', () => {
  if (exiting) return;
  exiting = true;
  pb.realtime.unsubscribeByPrefix('messages');
  // If subscribed, exit cleanly; otherwise timeout to 0 anyway
  setTimeout(() => { process.exit(0); }, 2500);
});

process.on('SIGINT', () => {
  if (exiting) return;
  exiting = true;
  pb.realtime.unsubscribeByPrefix('messages');
  setTimeout(() => { process.exit(0); }, 2500);
});

main().catch((err) => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
