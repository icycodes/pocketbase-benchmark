import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	// Initialize a new PocketBase instance for each request
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load the auth store from the incoming request cookie
	event.locals.pb.authStore.loadFromCookie(event.request.headers.get('cookie') || '');

	try {
		// Refresh the auth token if the store is valid
		if (event.locals.pb.authStore.isValid) {
			await event.locals.pb.collection('users').authRefresh();
		}
	} catch (_) {
		// If the token is invalid or expired, clear the auth store
		event.locals.pb.authStore.clear();
	}

	// Resolve the route handler
	const response = await resolve(event);

	// Write the updated auth state back to the response as a pb_auth cookie
	const cookie = event.locals.pb.authStore.exportToCookie({ httpOnly: false });
	if (cookie) {
		response.headers.append('set-cookie', cookie);
	}

	return response;
}
