import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load the auth store state from the request cookie
	event.locals.pb.authStore.loadFromCookie(event.request.headers.get('cookie') || '');

	try {
		// If the auth store has a valid token, refresh it to ensure it's still valid
		if (event.locals.pb.authStore.isValid) {
			await event.locals.pb.collection('users').authRefresh();
		}
	} catch (_) {
		// If the refresh fails, clear the auth store
		event.locals.pb.authStore.clear();
	}

	const response = await resolve(event);

	// Serialize the updated auth store state back to the response set-cookie header
	const cookie = event.locals.pb.authStore.exportToCookie({ httpOnly: false });
	if (cookie) {
		response.headers.append('set-cookie', cookie);
	}

	return response;
}
