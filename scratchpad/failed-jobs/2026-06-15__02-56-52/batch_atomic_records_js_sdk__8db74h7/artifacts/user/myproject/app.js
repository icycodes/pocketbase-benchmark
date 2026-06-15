const PocketBase = require('pocketbase/cjs');

async function main() {
    const args = process.argv.slice(2);
    let itemsCount = 0;
    let failMode = false;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--items') {
            itemsCount = parseInt(args[i + 1], 10);
            i++;
        } else if (args[i] === '--fail') {
            failMode = true;
        }
    }

    const PB = PocketBase.default || PocketBase;
    const pb = new PB(process.env.PB_URL);

    try {
        await pb.admins.authWithPassword(process.env.PB_ADMIN_EMAIL, process.env.PB_ADMIN_PASSWORD);
    } catch (e) {
        console.error("Auth failed:", e.message);
        process.exit(1);
    }

    const batch = pb.createBatch();

    // Generate a valid 15-char ID
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let orderId = '';
    for (let i = 0; i < 15; i++) {
        orderId += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    batch.collection('orders').create({
        id: orderId,
        customer: process.env.ZEALT_RUN_ID
    });

    for (let i = 0; i < itemsCount; i++) {
        batch.collection('order_items').create({
            order: orderId,
            product: 'product_' + i,
            quantity: 1
        });
    }

    if (failMode) {
        batch.collection('orders').create({
            id: 'invalid_id_format_too_long_or_something',
            customer: 'fail'
        });
    }

    try {
        await batch.send();
        console.log(`ORDER:${orderId}`);
        process.exit(0);
    } catch (err) {
        if (failMode) {
            console.error('BATCH_ROLLED_BACK');
            process.exit(1);
        } else {
            console.error("Batch failed:", err.message);
            process.exit(1);
        }
    }
}

main();