# Atomic Order + Items Creation with PocketBase JS SDK Batch API

## Goal
Write a Node.js script at `/home/user/myproject/app.js` that uses the PocketBase JavaScript SDK to atomically create one `orders` record together with N related `order_items` records in a single transactional batch request against the locally running PocketBase v0.31.0 server (Batch API enabled). The script must support a `--fail` mode where the entire batch must roll back.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `node app.js --items <N>` exits with code 0 and prints exactly one line to stdout matching the regex `^ORDER:[a-z0-9]{15}$` (where the suffix is the id of the newly created order). After execution, the PocketBase server must contain exactly 1 new `orders` row with its `customer` field equal to the value of the `ZEALT_RUN_ID` environment variable, and exactly N new `order_items` rows whose `order` relation field references the printed order id.
- Command: `node app.js --items <N> --fail` exits with code 1, emits the literal token `BATCH_ROLLED_BACK` on stderr, and produces NO new persisted `orders` or `order_items` rows (the batch must be fully rolled back).
- The script must perform the writes using the SDK batch interface (`pb.createBatch()` + `batch.send()`); it must not fall back to issuing one create request per item.
- Credentials and endpoint are available in the environment as `PB_URL`, `PB_ADMIN_EMAIL`, `PB_ADMIN_PASSWORD`; the `ZEALT_RUN_ID` value must be read from `$ZEALT_RUN_ID`.

