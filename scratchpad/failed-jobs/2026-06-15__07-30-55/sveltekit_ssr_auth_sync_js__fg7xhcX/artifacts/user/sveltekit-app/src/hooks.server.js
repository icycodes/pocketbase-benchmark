import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	// Create a new PocketBase instance per request to avoid shared state
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load auth state from the request cookie
	event.locals.pb.authStore.loadFromCookie(
		event.request.headers.get('cookie') || ''
	);

	// Attempt to refresh the token to verify it is still valid
	if (event.locals.pb.authStore.isValid) {
		try {
			await event.locals.pb.collection('users').authRefresh();
		} catch (_) {
			// Token is invalid or expired — clear the auth store
			event.locals.pb.authStore.clear();
		}
	}

	const response = await resolve(event);

	// Serialize the (possibly updated) auth state back to the response cookie
	response.headers.append(
		'set-cookie',
		event.locals.pb.authStore.exportToCookie({ httpOnly: true, secure: false })
	);

	return response;
}
