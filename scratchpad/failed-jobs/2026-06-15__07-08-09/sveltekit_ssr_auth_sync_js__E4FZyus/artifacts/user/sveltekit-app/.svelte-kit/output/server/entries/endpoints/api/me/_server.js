import { json } from "@sveltejs/kit";
async function GET({ locals }) {
  if (!locals.pb || !locals.pb.authStore.isValid || !locals.pb.authStore.model) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }
  return json({
    email: locals.pb.authStore.model.email
  });
}
export {
  GET
};
