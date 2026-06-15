routerAdd("GET", "/api/stats", (e) => {
    const result = new DynamicModel({
        "count": 0,
        "sum": 0,
    })

    try {
        // v0.22 and below
        $app.dao().db().newQuery("SELECT count(id) as count, COALESCE(sum(score), 0) as sum FROM game_scores").one(result)
    } catch (err) {
        // v0.23+
        try {
            $app.db().newQuery("SELECT count(id) as count, COALESCE(sum(score), 0) as sum FROM game_scores").one(result)
        } catch (err2) {
            console.log("Error querying stats:", err2);
            return e.json(500, {error: err2.message})
        }
    }

    return e.json(200, {
        count: result.count || 0,
        sum: result.sum || 0
    })
})
