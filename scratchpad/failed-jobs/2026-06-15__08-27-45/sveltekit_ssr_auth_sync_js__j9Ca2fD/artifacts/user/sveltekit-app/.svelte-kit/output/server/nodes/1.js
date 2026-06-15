

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.D7x9wL9w.js","_app/immutable/chunks/B2QSKqcC.js","_app/immutable/chunks/BoPpCq9m.js","_app/immutable/chunks/DkMDv_ll.js"];
export const stylesheets = [];
export const fonts = [];
