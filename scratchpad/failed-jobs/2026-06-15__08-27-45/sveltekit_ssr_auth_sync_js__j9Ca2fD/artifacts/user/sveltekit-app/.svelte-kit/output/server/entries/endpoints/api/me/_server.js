import { json } from "@sveltejs/kit";
async function GET({ locals }) {
  if (!locals.pb.authStore.isValid) {
    return new Response(null, { status: 401 });
  }
  return json({ email: locals.pb.authStore.model.email });
}
export {
  GET
};
