import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function POST({ request, locals }) {
    const { email, password } = await request.json();

    try {
        await locals.pb.collection('users').authWithPassword(email, password);
        return json({ success: true });
    } catch (err) {
        return json({ error: err.message }, { status: 400 });
    }
}
