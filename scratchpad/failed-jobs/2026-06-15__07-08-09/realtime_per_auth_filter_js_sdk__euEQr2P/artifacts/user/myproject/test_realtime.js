global.EventSource = require('eventsource').EventSource;
const PocketBase = require('pocketbase').default;
const { execSync, spawn } = require('child_process');
const http = require('http');

function isPocketBaseRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:8090/api/health', (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => {
      resolve(false);
    });
  });
}

async function main() {
  let pbProcess = null;
  let startedByUs = false;

  try {
    const running = await isPocketBaseRunning();
    if (!running) {
      console.log("PocketBase is not running. Starting it...");
      // Ensure superuser exists
      try {
        execSync('/usr/local/bin/pocketbase superuser upsert admin@example.com admin123456 --dir="/home/user/myproject/pb_data"');
      } catch (e) {
        console.warn("Failed to upsert superuser:", e.message);
      }

      // Start PocketBase
      pbProcess = spawn('/usr/local/bin/pocketbase', [
        'serve',
        '--http=127.0.0.1:8090',
        '--dir=/home/user/myproject/pb_data'
      ], { stdio: 'ignore' });
      startedByUs = true;

      // Wait for PocketBase to start
      let healthy = false;
      for (let i = 0; i < 20; i++) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        if (await isPocketBaseRunning()) {
          healthy = true;
          console.log("PocketBase started successfully and is healthy!");
          break;
        }
      }

      if (!healthy) {
        throw new Error("PocketBase failed to start after 10 seconds.");
      }
    } else {
      console.log("PocketBase is already running.");
    }

    // Connect to PocketBase
    const pbAdmin = new PocketBase('http://127.0.0.1:8090');
    await pbAdmin.admins.authWithPassword('admin@example.com', 'admin123456');

    // 1. Recreate messages collection
    try {
      await pbAdmin.collections.delete('messages');
      console.log("Deleted old messages collection");
    } catch (e) {}

    const collection = await pbAdmin.collections.create({
      name: 'messages',
      type: 'base',
      listRule: 'user = @request.auth.id',
      viewRule: 'user = @request.auth.id',
      createRule: '@request.auth.id != ""',
      updateRule: 'user = @request.auth.id',
      deleteRule: 'user = @request.auth.id',
      fields: [
        {
          name: 'user',
          type: 'relation',
          required: true,
          collectionId: '_pb_users_auth_',
          maxSelect: 1,
        }
      ]
    });
    console.log("Created messages collection with ListRule: user = @request.auth.id");

    // 2. Recreate User A and User B
    const users = await pbAdmin.collection('users').getFullList();
    for (const user of users) {
      if (user.email === 'usera@example.com' || user.email === 'userb@example.com') {
        await pbAdmin.collection('users').delete(user.id);
        console.log(`Deleted existing user: ${user.email}`);
      }
    }

    const userA = await pbAdmin.collection('users').create({
      email: 'usera@example.com',
      password: 'password123456',
      passwordConfirm: 'password123456',
    });
    console.log("Created User A:", userA.id);

    const userB = await pbAdmin.collection('users').create({
      email: 'userb@example.com',
      password: 'password123456',
      passwordConfirm: 'password123456',
    });
    console.log("Created User B:", userB.id);

    // 3. Authenticate as User A and subscribe to 'messages'
    const pbUserA = new PocketBase('http://127.0.0.1:8090');
    await pbUserA.collection('users').authWithPassword('usera@example.com', 'password123456');

    const receivedEvents = [];
    const unsubscribe = await pbUserA.collection('messages').subscribe('*', (e) => {
      console.log(`User A received event: ${e.action} for record ${e.record.id} (user: ${e.record.user})`);
      receivedEvents.push(e);
    });
    console.log("User A subscribed to messages collection");

    // Wait a brief moment to ensure SSE connection is fully established
    await new Promise((resolve) => setTimeout(resolve, 500));

    // 4. Create message for User A and message for User B (using admin client)
    console.log("Creating message assigned to User A...");
    const msgA = await pbAdmin.collection('messages').create({
      user: userA.id,
    });

    console.log("Creating message assigned to User B...");
    const msgB = await pbAdmin.collection('messages').create({
      user: userB.id,
    });

    // Wait for events to be processed
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Clean up subscription
    await unsubscribe();
    console.log("User A unsubscribed");

    // 5. Verify results
    console.log("Received events count:", receivedEvents.length);
    const receivedMsgIds = receivedEvents.map(e => e.record.id);
    console.log("Received message IDs:", receivedMsgIds);

    const hasMsgA = receivedMsgIds.includes(msgA.id);
    const hasMsgB = receivedMsgIds.includes(msgB.id);

    if (hasMsgA && !hasMsgB) {
      console.log("Test passed!");
      if (startedByUs && pbProcess) {
        pbProcess.kill();
        console.log("Stopped PocketBase server");
      }
      process.exit(0);
    } else {
      console.error(`Assertion failed: Expected only message A (${msgA.id}) but received:`, receivedMsgIds);
      if (startedByUs && pbProcess) {
        pbProcess.kill();
      }
      process.exit(1);
    }

  } catch (err) {
    console.error("Test failed with error:", err);
    if (startedByUs && pbProcess) {
      pbProcess.kill();
    }
    process.exit(1);
  }
}

main();
