const PocketBase = require('pocketbase/cjs');
const pb = new PocketBase('http://127.0.0.1:8090');
console.log(typeof pb.filter);
console.log(pb.filter('chat={:chat}', { chat: 'A' }));
