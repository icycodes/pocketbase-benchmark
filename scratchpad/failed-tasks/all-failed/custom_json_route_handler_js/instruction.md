# Custom JSON Route Handler for Aggregated Stats

## Background
PocketBase allows developers to extend its core functionality using server-side JavaScript via hooks and custom routes. In this task, you will implement a custom route that queries a collection, aggregates data, and returns the result as JSON.

## Requirements
- Ensure the `game_scores` collection exists in the database. You must create it (e.g., via a JS migration in `pb_migrations` or directly using the Admin UI). It must be of type `base`, have a `score` field of type `number`, and allow public create and read access (set API rules to `""`).
- Extend PocketBase by creating a custom route handler in JavaScript.
- Register a `GET` route at `/api/stats`.
- The handler must query the `game_scores` collection to calculate the total number of records (`count`) and the total sum of the `score` field (`sum`).
- Return the aggregated statistics as a JSON response.

## Implementation Hints
- Place your JavaScript code in the `pb_hooks` directory so PocketBase automatically loads it.
- Use `routerAdd` to register the custom route.
- Use `$app.db().newQuery(...)` or `$app.dao().db().newQuery(...)` (depending on your PocketBase version) to execute an aggregation query (e.g., `SELECT count(id) as total_count, sum(score) as total_score FROM game_scores`).
- Create a `new DynamicModel({...})` to define the shape of the data and populate it using the `.one()` method.
- Use `e.json(200, ...)` to send the response.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http=0.0.0.0:8090
- Port: 8090
- API Endpoints:
  - GET `/api/stats`: Returns status 200 and a JSON object containing the aggregated stats.

    ```json
    // Response
    {
      "count": number,
      "sum": number
    }
    ```

