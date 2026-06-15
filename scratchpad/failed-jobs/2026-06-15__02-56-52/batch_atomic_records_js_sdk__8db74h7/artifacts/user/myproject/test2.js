const PocketBase = require('pocketbase/cjs');
const PB = PocketBase.default || PocketBase;
const pb = new PB(process.env.PB_URL);
async function run() {
    await pb.admins.authWithPassword(process.env.PB_ADMIN_EMAIL, process.env.PB_ADMIN_PASSWORD);
    const batch = pb.createBatch();
    const orderId = 'a1b2c3d4e5f6g7h';
    batch.collection('orders').create({ id: orderId, customer: process.env.ZEALT_RUN_ID || 'test' });
    batch.collection('order_items').create({ order: orderId });
    try {
        await batch.send();
        console.log("Success");
    } catch(e) {
        console.log(JSON.stringify(e.response, null, 2));
    }
}
run();
