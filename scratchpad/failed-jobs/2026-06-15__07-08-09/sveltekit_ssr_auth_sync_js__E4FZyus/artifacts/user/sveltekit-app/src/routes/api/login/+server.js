import { json } from '@sveltejs/kit';

export async function POST({ request, locals }) {
    try {
        const { email, password } = await request.json();

        if (!email || !password) {
            return json({ error: 'Email and password are required' }, { status: 400 });
        }

        // Authenticate with PocketBase
        await locals.pb.collection('users').authWithPassword(email, password);

        // Return 200 OK with a JSON response
        return json({ success: true });
    } catch (err) {
        return json({ error: err.message || 'Authentication failed' }, { status: 400 });
    }
}
