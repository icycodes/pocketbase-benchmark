import { json } from "@sveltejs/kit";
async function POST({ request, locals }) {
  const { email, password } = await request.json();
  await locals.pb.collection("users").authWithPassword(email, password);
  return json({});
}
export {
  POST
};
