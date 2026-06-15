import { json } from "@sveltejs/kit";
async function POST({ request, locals }) {
  try {
    const { email, password } = await request.json();
    if (!email || !password) {
      return json({ error: "Email and password are required" }, { status: 400 });
    }
    await locals.pb.collection("users").authWithPassword(email, password);
    return json({ success: true });
  } catch (err) {
    return json({ error: err.message || "Authentication failed" }, { status: 400 });
  }
}
export {
  POST
};
