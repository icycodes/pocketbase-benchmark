/// <reference path="../pb_data/types.d.ts" />

onBootstrap((e) => {
  try {
    e.next();
    console.log("Bootstrap hook started");
    
    // Ensure the users collection create rule is open
    const usersCollection = e.app.findCollectionByNameOrId("users");
    if (usersCollection) {
      usersCollection.createRule = "";
      e.app.save(usersCollection);
      console.log("Users collection create rule set to open");
    }

    // Ensure rate limit table is created
    e.app.db().newQuery(`
      CREATE TABLE IF NOT EXISTS signup_rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        timestamp INTEGER
      )
    `).execute();
    console.log("signup_rate_limits table verified/created");
  } catch (err) {
    console.log("Bootstrap error: " + err);
  }
});

routerUse((e) => {
  try {
    const method = e.request.method;
    const path = e.request.url.path;
    console.log("Middleware executed for method: " + method + ", path: " + path);

    // Normalize path by stripping trailing slash
    const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;

    if (method === "POST" && normalizedPath === "/api/collections/users/records") {
      console.log("Target endpoint matched!");
      // Determine client IP
      let ip = e.request.header.get("X-Forwarded-For") || e.request.header.get("X-Real-IP");
      if (ip) {
        if (ip.indexOf(",") !== -1) {
          ip = ip.split(",")[0].trim();
        }
      }
      if (!ip) {
        ip = e.realIP() || e.remoteIP() || "unknown";
      }
      console.log("Client IP: " + ip);

      const now = Math.floor(Date.now() / 1000);
      const cutoff = now - 60;

      // Clean up old entries for this IP
      console.log("Cleaning up old entries older than: " + cutoff);
      e.app.db().newQuery("DELETE FROM signup_rate_limits WHERE timestamp <= {:cutoff}")
        .bind({ cutoff: cutoff })
        .execute();
      console.log("Cleanup done");

      // Count requests in the last 60 seconds
      console.log("Counting requests for IP: " + ip);
      const countResult = arrayOf(new DynamicModel({
        cnt: 0
      }));
      e.app.db().newQuery("SELECT COUNT(*) as cnt FROM signup_rate_limits WHERE ip = {:ip} AND timestamp > {:cutoff}")
        .bind({ ip: ip, cutoff: cutoff })
        .all(countResult);

      const count = countResult[0] ? parseInt(countResult[0].cnt, 10) : 0;
      console.log("Request count in window: " + count);

      if (count >= 3) {
        console.log("Rate limit exceeded!");
        // Find the oldest timestamp in the current window to calculate Retry-After
        const oldestResult = arrayOf(new DynamicModel({
          timestamp: 0
        }));
        e.app.db().newQuery("SELECT timestamp FROM signup_rate_limits WHERE ip = {:ip} AND timestamp > {:cutoff} ORDER BY timestamp ASC LIMIT 1")
          .bind({ ip: ip, cutoff: cutoff })
          .all(oldestResult);

        const oldestTime = oldestResult[0] ? parseInt(oldestResult[0].timestamp, 10) : cutoff;
        let retryAfter = (oldestTime + 60) - now;
        if (retryAfter < 1) {
          retryAfter = 1;
        }

        console.log("Returning 429. Retry-After: " + retryAfter);

        // Set Retry-After header
        e.response.header().set("Retry-After", retryAfter.toString());

        // Return 429 Too Many Requests response with custom JSON body
        return e.json(429, {
          retryAfter: retryAfter
        });
      }

      // If under limit, insert current attempt
      console.log("Inserting current attempt...");
      e.app.db().newQuery("INSERT INTO signup_rate_limits (ip, timestamp) VALUES ({:ip}, {:timestamp})")
        .bind({ ip: ip, timestamp: now })
        .execute();
      console.log("Inserted request into signup_rate_limits");
    }
  } catch (err) {
    console.log("Middleware error: " + err);
  }

  return e.next();
});
