/// <reference path="../pb_data/types.d.ts" />

/**
 * Per-IP rate limiter for POST /api/collections/users/records
 *
 * Allows 3 requests per IP within a rolling 60-second window.
 * The 4th+ request receives HTTP 429 with:
 *   - Response header: Retry-After: <seconds>
 *   - JSON body:       { "retryAfter": <seconds> }
 *
 * State is stored in $app.store() (concurrent-safe, process-lifetime
 * in-memory key-value store).
 *
 * Each callback has its own constants because PocketBase re-evaluates
 * the hook file in a fresh JS runtime for each invocation.
 */

// Prune stale store entries every minute
cronAdd("cleanup_signup_rate_limit", "* * * * *", function() {
    var WINDOW_SECONDS = 60;
    var KEY_PREFIX     = "rl_signup_";
    var nowSec         = Date.now() / 1000;
    var cutoff         = nowSec - WINDOW_SECONDS;
    var all            = $app.store().getAll();

    for (var key in all) {
        if (key.indexOf(KEY_PREFIX) !== 0) { continue; }
        var timestamps = JSON.parse(all[key] || "[]");
        timestamps = timestamps.filter(function(t) { return t > cutoff; });
        if (timestamps.length === 0) {
            $app.store().remove(key);
        } else {
            $app.store().set(key, JSON.stringify(timestamps));
        }
    }
});

// Rate-limit middleware — intercepts POST /api/collections/users/records
routerUse(function(e) {
    var RATE_LIMIT     = 3;
    var WINDOW_SECONDS = 60;
    var KEY_PREFIX     = "rl_signup_";

    var req  = e.request;
    var path = req.url.path;

    // Only apply to the users signup endpoint
    if (req.method !== "POST" || path !== "/api/collections/users/records") {
        return e.next();
    }

    var ip       = e.realIP() || "unknown";
    var storeKey = KEY_PREFIX + ip;
    var nowSec   = Date.now() / 1000;
    var cutoff   = nowSec - WINDOW_SECONDS;

    // Load existing timestamps from the store
    var raw        = $app.store().get(storeKey);
    var timestamps = raw ? JSON.parse(raw) : [];

    // Prune timestamps outside the current window
    timestamps = timestamps.filter(function(t) { return t > cutoff; });

    if (timestamps.length >= RATE_LIMIT) {
        // Time until the oldest request drops out of the window
        var oldest     = timestamps[0];
        var retryAfter = Math.ceil((oldest + WINDOW_SECONDS) - nowSec);
        if (retryAfter < 1) { retryAfter = 1; }

        e.response.header().set("Retry-After", String(retryAfter));
        return e.json(429, { retryAfter: retryAfter });
    }

    // Record this request and persist
    timestamps.push(nowSec);
    $app.store().set(storeKey, JSON.stringify(timestamps));

    return e.next();
});
