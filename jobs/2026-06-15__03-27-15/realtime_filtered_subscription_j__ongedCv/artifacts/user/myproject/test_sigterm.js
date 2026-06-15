const { EventSource } = require("eventsource");
global.EventSource = EventSource;

const PocketBase = require("pocketbase").default;

// Set up SIGTERM handler FIRST
process.on("SIGTERM", () => {
  process.stderr.write("SIGTERM received!\n");
  process.exit(0);
});

const pb = new PocketBase("http://127.0.0.1:8090");

pb.collection("_superusers").authWithPassword(
  process.env.PB_ADMIN_EMAIL,
  process.env.PB_ADMIN_PASSWORD
).then(() => {
  process.stderr.write("Authenticated\n");
  return pb.collection("messages").subscribe("*", (e) => {
    process.stdout.write(JSON.stringify({action: e.action, record: e.record}) + "\n");
  }, {
    filter: "chat='A'",
  });
}).then(() => {
  process.stderr.write("Subscribed\n");
}).catch((err) => {
  process.stderr.write("Error: " + err.message + "\n");
  process.exit(1);
});