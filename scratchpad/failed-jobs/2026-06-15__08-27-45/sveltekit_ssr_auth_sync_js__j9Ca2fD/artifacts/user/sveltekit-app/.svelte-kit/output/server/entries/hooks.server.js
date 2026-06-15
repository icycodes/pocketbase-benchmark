import PocketBase from "pocketbase";
async function handle({ event, resolve }) {
  event.locals.pb = new PocketBase("http://127.0.0.1:8090");
  event.locals.pb.authStore.loadFromCookie(event.request.headers.get("cookie") || "");
  try {
    if (event.locals.pb.authStore.isValid) {
      await event.locals.pb.collection("users").authRefresh();
    }
  } catch (_) {
    event.locals.pb.authStore.clear();
  }
  const response = await resolve(event);
  const cookie = event.locals.pb.authStore.exportToCookie({ httpOnly: false });
  if (cookie) {
    response.headers.append("set-cookie", cookie);
  }
  return response;
}
export {
  handle
};
