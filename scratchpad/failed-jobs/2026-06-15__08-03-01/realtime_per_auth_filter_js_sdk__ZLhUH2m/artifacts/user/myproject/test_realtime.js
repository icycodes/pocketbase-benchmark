// Polyfill EventSource for Node.js (required for PocketBase realtime)
global.EventSource = require('eventsource').EventSource;

const PocketBase = require('pocketbase').default;

const PB_URL = 'http://127.0.0.1:8090';
const ADMIN_EMAIL = 'admin@test.com';
const ADMIN_PASSWORD = 'admin123456';

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    try {
        // ===== Step 1: Set up admin client =====
        const adminPb = new PocketBase(PB_URL);
        await adminPb.admins.authWithPassword(ADMIN_EMAIL, ADMIN_PASSWORD);
        console.log('Admin authenticated successfully');

        // ===== Step 2: Clean up existing data =====
        // Delete messages collection if it exists
        try {
            const existingMessages = await adminPb.collections.getFirstListItem("name='messages'");
            await adminPb.collections.delete(existingMessages.id);
            console.log('Deleted existing messages collection');
        } catch (e) {
            // Collection doesn't exist, that's fine
        }

        // Delete any existing test users
        try {
            const existingUsers = await adminPb.collection('users').getFullList({
                filter: "email='userA@test.com' || email='userB@test.com'",
            });
            for (const u of existingUsers) {
                await adminPb.collection('users').delete(u.id);
                console.log('Deleted existing user:', u.email);
            }
        } catch (e) {
            // No users to delete
        }

        // ===== Step 3: Create messages collection with user relation and listRule =====
        const usersCollection = await adminPb.collections.getFirstListItem("name='users'");
        console.log('Users collection ID:', usersCollection.id);

        const messagesCollection = await adminPb.collections.create({
            name: 'messages',
            type: 'base',
            fields: [
                {
                    name: 'user',
                    type: 'relation',
                    collectionId: usersCollection.id,
                    required: true,
                    maxSelect: 1,
                    cascadeDelete: false,
                },
                {
                    name: 'content',
                    type: 'text',
                    required: false,
                },
            ],
            listRule: 'user = @request.auth.id',
            viewRule: 'user = @request.auth.id',
            createRule: '@request.auth.id != ""',
            updateRule: null,
            deleteRule: null,
        });
        console.log('Messages collection created:', messagesCollection.id);

        // ===== Step 4: Create two users =====
        const userA = await adminPb.collection('users').create({
            email: 'userA@test.com',
            password: 'password123',
            passwordConfirm: 'password123',
            name: 'User A',
        });
        console.log('User A created:', userA.id);

        const userB = await adminPb.collection('users').create({
            email: 'userB@test.com',
            password: 'password123',
            passwordConfirm: 'password123',
            name: 'User B',
        });
        console.log('User B created:', userB.id);

        // ===== Step 5: Authenticate as User A and subscribe to messages =====
        const userAPb = new PocketBase(PB_URL);
        await userAPb.collection('users').authWithPassword('userA@test.com', 'password123');
        console.log('User A authenticated successfully');

        const receivedEvents = [];

        // Subscribe to all messages events
        await userAPb.collection('messages').subscribe('*', (e) => {
            console.log('Received event:', e.action, 'record id:', e.record?.id, 'user:', e.record?.user);
            receivedEvents.push(e);
        });

        // Wait for the subscription to be fully established
        await sleep(1000);
        console.log('Subscription established');

        // ===== Step 6: Create messages as admin =====
        // Create a message assigned to User A
        const msgA = await adminPb.collection('messages').create({
            user: userA.id,
            content: 'Hello User A',
        });
        console.log('Message for User A created:', msgA.id);

        // Create a message assigned to User B
        const msgB = await adminPb.collection('messages').create({
            user: userB.id,
            content: 'Hello User B',
        });
        console.log('Message for User B created:', msgB.id);

        // Wait for SSE events to be processed
        await sleep(2000);

        // ===== Step 7: Unsubscribe =====
        await userAPb.collection('messages').unsubscribe('*');
        console.log('Unsubscribed from messages');

        // ===== Step 8: Verify results =====
        console.log('Total events received:', receivedEvents.length);

        // Filter for create events only
        const createEvents = receivedEvents.filter(e => e.action === 'create');

        console.log('Create events received:', createEvents.length);

        // Check that User A only received the event for their own message
        const userAEvents = createEvents.filter(e => e.record?.user === userA.id);
        const userBEvents = createEvents.filter(e => e.record?.user === userB.id);

        console.log('Events for User A message:', userAEvents.length);
        console.log('Events for User B message:', userBEvents.length);

        if (createEvents.length === 1 &&
            userAEvents.length === 1 &&
            userBEvents.length === 0) {
            console.log('Test passed!');
            process.exit(0);
        } else {
            console.error('Test failed!');
            console.error('Expected exactly 1 create event for User A, got:', createEvents.length);
            console.error('Expected 0 create events for User B, got:', userBEvents.length);
            process.exit(1);
        }
    } catch (error) {
        console.error('Test failed with error:', error?.message || error);
        console.error('Error response:', JSON.stringify(error?.response || error?.data || {}, null, 2));
        console.error(error?.stack || '');
        process.exit(1);
    }
}

main();