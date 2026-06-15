import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	// Initialize a new PocketBase instance for each request
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load auth state from the pb_auth cookie
	const cookie = event.request.headers.get('cookie') || '';
	event.locals.pb.authStore.loadFromCookie(cookie, 'pb_auth');

	try {
		// Attempt to refresh the authentication state if the store appears valid
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
	const pbAuthCookie = event.locals.pb.authStore.exportToCookie({}, 'pb_auth');

	// exportToCookie returns a raw Set-Cookie header string; append it to the response
	response.headers.append('set-cookie', pbAuthCookie);

	return response;
}