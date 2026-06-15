import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET({ locals }) {
    if (!locals.pb.authStore.isValid) {
        return json({ error: 'Unauthorized' }, { status: 401 });
    }

    return json({ email: locals.pb.authStore.model.email });
}
