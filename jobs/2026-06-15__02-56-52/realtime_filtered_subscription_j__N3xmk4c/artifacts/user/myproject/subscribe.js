const PocketBase = require('pocketbase/cjs');

async function main() {
  const args = process.argv.slice(2);
  let chatId = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--chat') {
      chatId = args[i + 1];
      break;
    }
  }

  if (!chatId) {
    console.error('Missing --chat argument');
    process.exit(1);
  }

  const pb = new PocketBase('http://127.0.0.1:8090');

  const email = process.env.PB_ADMIN_EMAIL;
  const password = process.env.PB_ADMIN_PASSWORD;

  if (email && password) {
    try {
      await pb.collection('_superusers').authWithPassword(email, password);
    } catch (err) {
      console.error('Auth failed:', err.message);
      process.exit(1);
    }
  }

  try {
    await pb.collection('messages').subscribe('*', function (e) {
      const out = {
        action: e.action,
        record: e.record
      };
      process.stdout.write(JSON.stringify(out) + '\n');
    }, { filter: pb.filter('chat={:chat}', { chat: chatId }) });
  } catch (err) {
    console.error('Subscribe failed:', err.message);
    process.exit(1);
  }

  process.on('SIGTERM', async () => {
    setTimeout(() => {
      process.exit(0);
    }, 2000).unref();

    try {
      await pb.collection('messages').unsubscribe('*');
    } catch (err) {
      // Ignore errors during unsubscribe
    }
    process.exit(0);
  });
}

main();