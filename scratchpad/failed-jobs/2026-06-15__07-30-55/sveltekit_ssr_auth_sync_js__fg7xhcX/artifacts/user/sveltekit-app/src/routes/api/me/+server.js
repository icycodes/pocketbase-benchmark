import { json, error } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET({ locals }) {
	if (!locals.pb.authStore.isValid) {
		throw error(401, 'Unauthorized');
	}

	return json({ email: locals.pb.authStore.model.email });
}
