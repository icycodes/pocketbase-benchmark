routerAdd("GET", "/api/stats", (e) => {
  const result = new DynamicModel({
    count: 0,
    sum: -0,
  });

  try {
    $app.db()
      .newQuery("SELECT count(id) as count, COALESCE(sum(score), 0) as sum FROM game_scores")
      .one(result);
  } catch (err) {
    return e.json(500, { error: err.message });
  }

  return e.json(200, {
    count: result.count,
    sum: result.sum,
  });
});
