import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	// Initialize a new PocketBase instance for this request
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load auth state from the incoming pb_auth cookie
	event.locals.pb.authStore.loadFromCookie(
		event.request.headers.get('cookie') || ''
	);

	// Attempt to refresh the auth token if the store is currently valid
	if (event.locals.pb.authStore.isValid) {
		try {
			await event.locals.pb.collection('users').authRefresh();
		} catch (_) {
			// Token is invalid or expired — clear the auth store
			event.locals.pb.authStore.clear();
		}
	}

	// Resolve the request
	const response = await resolve(event);

	// Write the updated auth state back as a pb_auth cookie in the response
	response.headers.append(
		'set-cookie',
		event.locals.pb.authStore.exportToCookie({ httpOnly: true, secure: false })
	);

	return response;
}
