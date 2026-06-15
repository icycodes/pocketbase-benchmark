const PocketBase = require('pocketbase/cjs');
const { EventSource } = require('eventsource');
global.EventSource = EventSource;

const pb = new PocketBase('http://127.0.0.1:8090');

async function run() {
    try {
        const adminEmail = 'admin_' + Date.now() + '@example.com';
        const adminPassword = 'password123456';
        
        try {
            await pb.admins.create({
                email: adminEmail,
                password: adminPassword,
                passwordConfirm: adminPassword
            });
        } catch (e) {
            // Ignore if creation fails
        }
        
        try {
            await pb.admins.authWithPassword(adminEmail, adminPassword);
        } catch (e) {
            // Fallback to the one we created in test.js if needed
            await pb.admins.authWithPassword('admin@example.com', 'password123456');
        }

        const usersCollection = await pb.collections.getOne('users');

        try {
            const existingMessages = await pb.collections.getOne('messages');
            if (existingMessages) {
                await pb.collections.delete('messages');
            }
        } catch (e) {
            // Collection doesn't exist, which is fine
        }

        await pb.collections.create({
            name: 'messages',
            type: 'base',
            schema: [
                {
                    name: 'user',
                    type: 'relation',
                    required: true,
                    options: {
                        collectionId: usersCollection.id,
                        cascadeDelete: true,
                        maxSelect: 1
                    }
                },
                {
                    name: 'text',
                    type: 'text',
                    required: false
                }
            ],
            listRule: 'user = @request.auth.id',
            viewRule: 'user = @request.auth.id',
            createRule: null,
            updateRule: null,
            deleteRule: null
        });

        const userAEmail = 'usera_' + Date.now() + '@example.com';
        const userBEmail = 'userb_' + Date.now() + '@example.com';

        const userA = await pb.collection('users').create({
            email: userAEmail,
            password: 'password123456',
            passwordConfirm: 'password123456',
            emailVisibility: true,
            verified: true
        });

        const userB = await pb.collection('users').create({
            email: userBEmail,
            password: 'password123456',
            passwordConfirm: 'password123456',
            emailVisibility: true,
            verified: true
        });

        const pbUserA = new PocketBase('http://127.0.0.1:8090');
        await pbUserA.collection('users').authWithPassword(userAEmail, 'password123456');

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

    } catch (err) {
        console.error('Error:', err);
        process.exit(1);
    }
}

run();