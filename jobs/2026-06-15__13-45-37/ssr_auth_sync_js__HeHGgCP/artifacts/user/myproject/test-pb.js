const PocketBase = require('pocketbase').default;

async function main() {
  const pb = new PocketBase('http://127.0.0.1:8090');
  try {
    const authData = await pb.collection('users').authWithPassword('test@example.com', 'secure_password');
    console.log('Authentication successful!');
    console.log('User ID:', authData.record.id);
    console.log('User Email:', authData.record.email);
    console.log('Cookie:', pb.authStore.exportToCookie());
  } catch (err) {
    console.error('Authentication failed:', err.message);
  }
}

main();
