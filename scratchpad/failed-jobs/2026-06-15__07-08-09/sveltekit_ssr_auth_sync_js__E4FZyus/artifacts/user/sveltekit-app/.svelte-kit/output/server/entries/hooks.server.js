import PocketBase from "pocketbase";
async function handle({ event, resolve }) {
  event.locals.pb = new PocketBase("http://127.0.0.1:8090");
  const cookieHeader = event.request.headers.get("cookie") || "";
  event.locals.pb.authStore.loadFromCookie(cookieHeader);
  try {
    if (event.locals.pb.authStore.isValid) {
      await event.locals.pb.collection("users").authRefresh();
    }
  } catch (err) {
    event.locals.pb.authStore.clear();
  }
  const response = await resolve(event);
  response.headers.append("set-cookie", event.locals.pb.authStore.exportToCookie({ secure: false }));
  return response;
}
export {
  handle
};
