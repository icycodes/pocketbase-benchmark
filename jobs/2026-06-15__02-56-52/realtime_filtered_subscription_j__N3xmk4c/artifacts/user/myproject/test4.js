const PocketBase = require('pocketbase/cjs');
const pb = new PocketBase('http://127.0.0.1:8090');
console.log(pb.collection('messages').unsubscribe('*') instanceof Promise);
