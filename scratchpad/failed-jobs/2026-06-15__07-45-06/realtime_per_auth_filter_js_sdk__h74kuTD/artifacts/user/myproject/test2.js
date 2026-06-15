const PocketBase = require('pocketbase/cjs');
const { EventSource } = require('eventsource');
global.EventSource = EventSource;

const pb = new PocketBase('http://127.0.0.1:8090');

async function run() {
    try {
        const adminEmail = 'admin@example.com';
        const adminPassword = 'password123456';
        
        await pb.admins.authWithPassword(adminEmail, adminPassword);

        // Delete users if they exist
        try {
            const users = await pb.collection('users').getFullList();
            for (const u of users) {
                await pb.collection('users').delete(u.id);
            }
        } catch(e) {}

        const userA = await pb.collection('users').create({
            email: 'usera@example.com',
            password: 'password123456',
            passwordConfirm: 'password123456',
            emailVisibility: true,
            verified: true
        });

        const userB = await pb.collection('users').create({
            email: 'userb@example.com',
            password: 'password123456',
            passwordConfirm: 'password123456',
            emailVisibility: true,
            verified: true
        });

        const pbUserA = new PocketBase('http://127.0.0.1:8090');
        await pbUserA.collection('users').authWithPassword('usera@example.com', 'password123456');

        const receivedEvents = [];

        await pbUserA.collection('messages').subscribe('*', (e) => {
            receivedEvents.push(e);
        });

        await new Promise(resolve => setTimeout(resolve, 1000));

        const msgA = await pb.collection('messages').create({
            user: userA.id,
            text: 'Message for User A'
        });

        const msgB = await pb.collection('messages').create({
            user: userB.id,
            text: 'Message for User B'
        });

        await new Promise(resolve => setTimeout(resolve, 1000));

        await pbUserA.collection('messages').unsubscribe('*');

        if (receivedEvents.length === 1 && receivedEvents[0].record.id === msgA.id) {
            console.log('Test passed!');
            process.exit(0);
        } else {
            console.error('Test failed! Received events:', receivedEvents);
            process.exit(1);
        }
    } catch(e) {
        console.error(e);
        process.exit(1);
    }
}
run();