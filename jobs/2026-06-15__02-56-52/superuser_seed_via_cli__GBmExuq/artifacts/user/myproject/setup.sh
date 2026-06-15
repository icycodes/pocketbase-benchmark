#!/bin/bash
set -e

cd /home/user/myproject

# 1. Create superuser
./pocketbase superuser upsert admin@example.com Adm1n_passw0rd!

# 2. Apply migration
mkdir -p pb_migrations
cat << 'MIGRATE_EOF' > pb_migrations/1000000000_tasks.js
/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  try {
    app.findCollectionByNameOrId("tasks");
  } catch (e) {
    const collection = new Collection({
      type: "base",
      name: "tasks",
      fields: [
        {
          name: "title",
          type: "text",
          required: true
        },
        {
          name: "done",
          type: "bool"
        },
        {
          name: "due",
          type: "date"
        }
      ]
    });
    app.save(collection);
  }
}, (app) => {
  try {
    const collection = app.findCollectionByNameOrId("tasks");
    app.delete(collection);
  } catch (e) {}
})
MIGRATE_EOF

./pocketbase migrate

# 3. Start server in background
if ! curl -s --max-time 1 http://127.0.0.1:8090/api/health > /dev/null; then
  ./pocketbase serve --http 127.0.0.1:8090 > /dev/null 2>&1 &
  while ! curl -s --max-time 1 http://127.0.0.1:8090/api/health > /dev/null; do
    sleep 0.5
  done
fi

# 4. Seed tasks
TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/collections/_superusers/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{"identity":"admin@example.com","password":"Adm1n_passw0rd!"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4)

python3 - <<PY_EOF
import urllib.request
import json
import sys

token = "$TOKEN"
base_url = "http://127.0.0.1:8090/api/collections/tasks/records"
fetch_url = base_url + "?perPage=500"

tasks = [
    "Buy groceries",
    "Walk the dog",
    "Read a book",
    "Write weekly report",
    "Call mom"
]

req = urllib.request.Request(fetch_url, headers={"Authorization": token})
response = urllib.request.urlopen(req)
data = json.loads(response.read())

existing_tasks = {item["title"] for item in data.get("items", [])}

for task in tasks:
    if task not in existing_tasks:
        post_data = json.dumps({"title": task}).encode("utf-8")
        post_req = urllib.request.Request(base_url, data=post_data, headers={
            "Authorization": token,
            "Content-Type": "application/json"
        })
        urllib.request.urlopen(post_req)
PY_EOF
