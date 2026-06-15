const PocketBase = require('pocketbase').default;

function generateId() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let id = '';
    for (let i = 0; i < 15; i++) {
        id += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return id;
}

async function main() {
    const args = process.argv.slice(2);
    const itemsIndex = args.indexOf('--items');
    const failMode = args.includes('--fail');

    if (itemsIndex === -1 || !args[itemsIndex + 1]) {
        console.error('Usage: node app.js --items <N> [--fail]');
        process.exit(1);
    }

    const N = parseInt(args[itemsIndex + 1], 10);

    const pb = new PocketBase(process.env.PB_URL);

    // Authenticate as superuser
    await pb.collection('_superusers').authWithPassword(
        process.env.PB_ADMIN_EMAIL,
        process.env.PB_ADMIN_PASSWORD
    );

    const runId = process.env.ZEALT_RUN_ID;

    // Generate a custom ID for the order so we can reference it in order_items
    const orderId = generateId();

    const batch = pb.createBatch();

    // Create order with a custom ID at batch index 0
    batch.collection('orders').create({
        id: orderId,
        customer: runId,
        total: 0
    });

    // Create N order_items referencing the order by its custom ID
    for (let i = 0; i < N; i++) {
        batch.collection('order_items').create({
            order: orderId,
            product: 'Product ' + (i + 1),
            quantity: 1
        });
    }

    if (failMode) {
        // Add a request that will intentionally fail to trigger a full rollback.
        // Creating a record in a non-existent collection causes a 404 error.
        batch.requests.push({
            method: 'POST',
            url: '/api/collections/nonexistent_collection/records',
            headers: {},
            json: {},
            files: {}
        });
    }

    try {
        const result = await batch.send();
        // The batch response is an array of { body, status } objects
        const items = Array.isArray(result) ? result : (result.items || result);
        const createdOrderId = items[0].body.id;
        console.log('ORDER:' + createdOrderId);
        process.exit(0);
    } catch (error) {
        if (failMode) {
            process.stderr.write('BATCH_ROLLED_BACK\n');
            process.exit(1);
        }
        console.error('Batch failed:', error.message || error);
        process.exit(1);
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});