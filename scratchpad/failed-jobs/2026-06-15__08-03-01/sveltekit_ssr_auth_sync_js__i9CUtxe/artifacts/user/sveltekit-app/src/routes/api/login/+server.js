import { json } from '@sveltejs/kit';

export async function POST({ request, locals }) {
	const { email, password } = await request.json();

	try {
		await locals.pb.collection('users').authWithPassword(email, password);
		return json({ success: true });
	} catch (error) {
		return json({ success: false, error: error.message }, { status: 401 });
	}
}