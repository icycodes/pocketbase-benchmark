import { EventSource } from 'eventsource';
import PocketBase from 'pocketbase';

// Set EventSource globally for PocketBase SDK
global.EventSource = EventSource;

// Parse command line arguments
const args = process.argv.slice(2);
let chatId = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--chat' && i + 1 < args.length) {
    chatId = args[i + 1];
    break;
  }
}

if (!chatId) {
  console.error('Error: --chat <chatId> is required.');
  process.exit(1);
}

const adminEmail = process.env.PB_ADMIN_EMAIL;
const adminPassword = process.env.PB_ADMIN_PASSWORD;

if (!adminEmail || !adminPassword) {
  console.error('Error: PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD environment variables are required.');
  process.exit(1);
}

const pb = new PocketBase('http://127.0.0.1:8090');

// Handle SIGTERM
process.on('SIGTERM', () => {
  process.exit(0);
});

async function run() {
  try {
    // Authenticate as superuser
    await pb.collection('_superusers').authWithPassword(adminEmail, adminPassword);
    
    // Subscribe with filter
    await pb.collection('messages').subscribe('*', (e) => {
      const output = JSON.stringify({
        action: e.action,
        record: e.record
      });
      process.stdout.write(output + '\n');
    }, {
      filter: pb.filter('chat = {:chatId}', { chatId })
    });

  } catch (error) {
    console.error('Error in subscribe script:', error);
    process.exit(1);
  }
}

run();
