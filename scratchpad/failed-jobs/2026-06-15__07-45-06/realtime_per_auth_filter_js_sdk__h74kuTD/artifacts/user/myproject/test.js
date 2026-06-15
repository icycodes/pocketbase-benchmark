const PocketBase = require('pocketbase/cjs');
const EventSource = require('eventsource');
global.EventSource = EventSource;

const pb = new PocketBase('http://127.0.0.1:8090');

async function run() {
    try {
        const adminEmail = 'admin@example.com';
        const adminPassword = 'password123456';
        
        try {
            await pb.admins.create({
                email: adminEmail,
                password: adminPassword,
                passwordConfirm: adminPassword
            });
        } catch (e) {}
        
        await pb.admins.authWithPassword(adminEmail, adminPassword);
        
        const usersCollection = await pb.collections.getOne('users');

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
            createRule: '',
            updateRule: '',
            deleteRule: ''
        });
        console.log("Collection created");
    } catch(e) {
        console.log(e.response);
    }
}
run();