

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.CdFrZDS7.js","_app/immutable/chunks/B2QSKqcC.js","_app/immutable/chunks/BoPpCq9m.js"];
export const stylesheets = [];
export const fonts = [];
