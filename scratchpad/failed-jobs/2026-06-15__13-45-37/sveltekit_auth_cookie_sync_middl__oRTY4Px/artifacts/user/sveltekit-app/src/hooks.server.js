import PocketBase from 'pocketbase';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
    // Initialize PocketBase instance
    event.locals.pb = new PocketBase('http://127.0.0.1:8090');

    // Read the pb_auth cookie from the incoming request and load it into the PocketBase auth store
    const cookieHeader = event.request.headers.get('cookie') || '';
    event.locals.pb.authStore.loadFromCookie(cookieHeader);

    // Attempt to refresh the authentication state using authRefresh() on the users collection
    if (event.locals.pb.authStore.isValid) {
        try {
            await event.locals.pb.collection('users').authRefresh();
        } catch (_) {
            // If refresh fails, clear the auth store
            event.locals.pb.authStore.clear();
        }
    }

    // Resolve the response
    const response = await resolve(event);

    // Write the updated auth state back to the response headers as a pb_auth cookie
    response.headers.append('set-cookie', event.locals.pb.authStore.exportToCookie());

    return response;
}
