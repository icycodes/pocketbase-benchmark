import PocketBase from 'pocketbase';

export async function handle({ event, resolve }) {
    event.locals.pb = new PocketBase('http://127.0.0.1:8090');

    // Load the auth store state from the request cookie
    const cookieHeader = event.request.headers.get('cookie') || '';
    event.locals.pb.authStore.loadFromCookie(cookieHeader);

    try {
        // Verify/refresh the auth store state if valid
        if (event.locals.pb.authStore.isValid) {
            await event.locals.pb.collection('users').authRefresh();
        }
    } catch (err) {
        // Clear the auth store if refresh fails
        event.locals.pb.authStore.clear();
    }

    const response = await resolve(event);

    // Serialize the updated auth store state back to the response set-cookie header
    response.headers.append('set-cookie', event.locals.pb.authStore.exportToCookie({ secure: false }));

    return response;
}
