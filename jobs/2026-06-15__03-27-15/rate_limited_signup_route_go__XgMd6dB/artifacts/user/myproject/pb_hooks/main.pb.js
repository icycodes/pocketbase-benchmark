/// <reference path="../pb_data/types.d.ts" />

// Per-IP rate limiter for POST /api/collections/users/records
// Limits to 3 signup requests per 60-second window per client IP

const RATE_LIMIT_MAX = 3;         // max requests per window
const RATE_LIMIT_WINDOW = 60;     // window size in seconds

// In-memory store: maps IP -> { startTime: seconds, count: number }
const rateLimits = new Map();

routerUse((e) => {
    // Only rate-limit POST requests
    if (e.request.method !== "POST") {
        return e.next();
    }

    // Only rate-limit the users signup endpoint
    const path = e.request.url.path;
    if (path !== "/api/collections/users/records" && path !== "/api/collections/users/records/") {
        return e.next();
    }

    const ip = e.remoteIP();
    const now = Math.floor(Date.now() / 1000);

    // Clean up expired entries
    for (const [key, entry] of rateLimits) {
        if (now - entry.startTime >= RATE_LIMIT_WINDOW) {
            rateLimits.delete(key);
        }
    }

    // Check rate limit
    let entry = rateLimits.get(ip);
    if (!entry || now - entry.startTime >= RATE_LIMIT_WINDOW) {
        // New window: first request or window expired
        rateLimits.set(ip, { startTime: now, count: 1 });
        return e.next();
    }

    // Window still active: increment count
    entry.count++;

    if (entry.count > RATE_LIMIT_MAX) {
        // Rate limit exceeded
        const retryAfter = Math.max(1, RATE_LIMIT_WINDOW - (now - entry.startTime));
        e.response.header().set("Retry-After", String(retryAfter));
        return e.json(429, { retryAfter: retryAfter });
    }

    return e.next();
});