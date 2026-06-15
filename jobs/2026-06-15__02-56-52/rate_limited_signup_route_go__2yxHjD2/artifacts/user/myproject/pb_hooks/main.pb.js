routerUse((e) => {
    let path = e.request.url.path;
    if (path.endsWith("/")) {
        path = path.slice(0, -1);
    }
    
    if (e.request.method === "POST" && path === "/api/collections/users/records") {
        const limit = 3;
        const windowMs = 60000;
        const ip = e.realIP();
        const nowMs = Date.now();
        
        const storeKey = "ratelimit_signup_" + ip;
        let rawHistory = $app.store().get(storeKey);
        let history = [];
        if (rawHistory && rawHistory.length) {
            for (let i = 0; i < rawHistory.length; i++) {
                history.push(rawHistory[i]);
            }
        }
        
        history = history.filter(t => nowMs - t < windowMs);
        
        if (history.length >= limit) {
            const oldestMs = history[0];
            let retryAfterSecs = Math.ceil((windowMs - (nowMs - oldestMs)) / 1000);
            if (retryAfterSecs < 1) retryAfterSecs = 1;
            
            e.response.header().set("Retry-After", String(retryAfterSecs));
            return e.json(429, { "retryAfter": retryAfterSecs });
        }
        
        history.push(nowMs);
        $app.store().set(storeKey, history);
    }
    return e.next();
})
