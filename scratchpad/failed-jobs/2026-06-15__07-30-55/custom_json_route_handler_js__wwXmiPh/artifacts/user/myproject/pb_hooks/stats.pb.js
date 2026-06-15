/// <reference path="../pb_data/types.d.ts" />

routerAdd("GET", "/api/stats", (e) => {
    const db = $app.db();

    const result = new DynamicModel({
        total_count: 0,
        total_score: 0,
    });

    db.newQuery(
        "SELECT count(id) as total_count, COALESCE(sum(score), 0) as total_score FROM game_scores"
    ).one(result);

    return e.json(200, {
        count: result.get("total_count"),
        sum:   result.get("total_score"),
    });
});
