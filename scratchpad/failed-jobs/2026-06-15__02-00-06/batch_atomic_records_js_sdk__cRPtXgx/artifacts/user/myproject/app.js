const PocketBase = require('pocketbase/cjs');

function generateId() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let id = '';
    for (let i = 0; i < 15; i++) {
        id += chars[Math.floor(Math.random() * chars.length)];
    }
    return id;
}

async function main() {
    // Parse arguments
    const args = process.argv.slice(2);
    let itemsCount = null;
    let failMode = false;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--items') {
            itemsCount = parseInt(args[i + 1], 10);
            i++;
        } else if (args[i] === '--fail') {
            failMode = true;
        }
    }

    if (itemsCount === null || isNaN(itemsCount) || itemsCount < 0) {
        console.error("Error: --items <N> is required and must be a non-negative integer.");
        process.exit(1);
    }

    // Initialize PocketBase client
    const pbUrl = process.env.PB_URL || 'http://127.0.0.1:8090';
    const pb = new PocketBase(pbUrl);

    try {
        // Authenticate as superuser/admin
        await pb.collection('_superusers').authWithPassword(
            process.env.PB_ADMIN_EMAIL,
            process.env.PB_ADMIN_PASSWORD
        );
    } catch (err) {
        console.error("Authentication failed:", err.message || err);
        process.exit(1);
    }

    // Create a batch request
    const batch = pb.createBatch();
    const orderId = generateId();

    // Add order creation to batch
    batch.collection('orders').create({
        id: orderId,
        customer: process.env.ZEALT_RUN_ID || '',
        total: itemsCount * 10
    });

    // Add order items to batch
    for (let i = 0; i < itemsCount; i++) {
        batch.collection('order_items').create({
            order: orderId,
            product: `Product ${i + 1}`,
            quantity: 1
        });
    }

    // If fail mode is enabled, add an invalid request to force batch rollback
    if (failMode) {
        batch.collection('order_items').create({
            order: orderId,
            // Omit required 'product' and 'quantity' to trigger validation failure
        });
    }

    try {
        await batch.send();
        
        if (failMode) {
            // Should not reach here because batch.send() should have failed
            console.error("Error: Batch succeeded unexpectedly in fail mode.");
            process.exit(1);
        }

        // Print exactly one line matching ORDER:[a-z0-9]{15} to stdout
        console.log(`ORDER:${orderId}`);
        process.exit(0);
    } catch (err) {
        if (failMode) {
            // Emit the literal token BATCH_ROLLED_BACK on stderr
            process.stderr.write("BATCH_ROLLED_BACK\n");
            process.exit(1);
        } else {
            console.error("Batch send failed:", err.message || err);
            process.exit(1);
        }
    }
}

main();
