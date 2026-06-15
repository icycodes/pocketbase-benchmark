import { c as create_ssr_component } from "../../chunks/ssr.js";
import { e as escape } from "../../chunks/escape.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let { data } = $$props;
  if ($$props.data === void 0 && $$bindings.data && data !== void 0) $$bindings.data(data);
  return `<h1 data-svelte-h="svelte-167jtqr">Hello PocketBase</h1> <p id="is-valid">Auth Store is valid: ${escape(data.isValid)}</p> ${data.isValid ? `<p id="user-email">User Email: ${escape(data.model?.email)}</p> <p id="token">Token: ${escape(data.token)}</p>` : `<p id="not-logged-in" data-svelte-h="svelte-mluqq4">Not logged in.</p>`}`;
});
export {
  Page as default
};
