import PocketBase from 'pocketbase';

export async function handle({ event, resolve }) {
	// Initialize a new PocketBase instance for each request
	event.locals.pb = new PocketBase('http://127.0.0.1:8090');

	// Load the auth state from the request cookie
	event.locals.pb.authStore.loadFromCookie(event.request.headers.get('cookie') || '');

	// Verify and refresh the auth token if valid
	try {
		if (event.locals.pb.authStore.isValid) {
			await event.locals.pb.collection('users').authRefresh();
		}
	} catch {
		// If refresh fails, clear the auth store
		event.locals.pb.authStore.clear();
	}

	// Resolve the event
	const response = await resolve(event);

	// Serialize the updated auth store state back to the response cookie
	response.headers.append('set-cookie', event.locals.pb.authStore.exportToCookie());

	return response;
}