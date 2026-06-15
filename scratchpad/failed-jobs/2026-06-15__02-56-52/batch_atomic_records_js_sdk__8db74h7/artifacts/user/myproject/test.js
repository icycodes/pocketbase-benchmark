const PocketBase = require('pocketbase/cjs');
const PB = PocketBase.default || PocketBase;
const pb = new PB(process.env.PB_URL);
async function run() {
    await pb.admins.authWithPassword(process.env.PB_ADMIN_EMAIL, process.env.PB_ADMIN_PASSWORD);
    const batch = pb.createBatch();
    batch.collection('orders').create({ customer: process.env.ZEALT_RUN_ID || 'test' });
    try {
        await batch.send();
        console.log("Success");
    } catch(e) {
        console.log(JSON.stringify(e.response, null, 2));
    }
}
run();
