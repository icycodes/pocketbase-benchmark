const { EventSource } = require("eventsource");
global.EventSource = EventSource;

const PocketBase = require("pocketbase").default;

// Parse --chat argument
const args = process.argv.slice(2);
let chatId = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--chat" && i + 1 < args.length) {
    chatId = args[i + 1];
    break;
  }
}

if (!chatId) {
  process.stderr.write("Usage: node subscribe.js --chat <chatId>\n");
  process.exit(1);
}

const pb = new PocketBase("http://127.0.0.1:8090");

// Authenticate as superuser so we can subscribe to the collection
pb.collection("_superusers").authWithPassword(
  process.env.PB_ADMIN_EMAIL,
  process.env.PB_ADMIN_PASSWORD
).then(() => {
  // Subscribe with server-side filter on the chat field
  return pb.collection("messages").subscribe("*", (e) => {
    // Map PocketBase action to the required output shape
    const output = {
      action: e.action,
      record: e.record,
    };

    process.stdout.write(JSON.stringify(output) + "\n");
  }, {
    filter: `chat='${chatId}'`,
  });
}).then(() => {
  // Handle SIGTERM: exit cleanly with status 0
  process.on("SIGTERM", () => {
    process.exit(0);
  });
}).catch((err) => {
  process.stderr.write("Error: " + err.message + "\n");
  process.exit(1);
});