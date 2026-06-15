/** @type {import('./$types').PageServerLoad} */
export function load({ locals }) {
    return {
        isValid: locals.pb.authStore.isValid,
        token: locals.pb.authStore.token,
        model: locals.pb.authStore.model ? {
            id: locals.pb.authStore.model.id,
            email: locals.pb.authStore.model.email
        } : null
    };
}
