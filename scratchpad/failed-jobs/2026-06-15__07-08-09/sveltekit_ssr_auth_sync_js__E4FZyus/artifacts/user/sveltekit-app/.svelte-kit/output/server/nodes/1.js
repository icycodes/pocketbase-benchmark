

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.CRKxrFyj.js","_app/immutable/chunks/B2QSKqcC.js","_app/immutable/chunks/BoPpCq9m.js","_app/immutable/chunks/QEiuX9l3.js"];
export const stylesheets = [];
export const fonts = [];
