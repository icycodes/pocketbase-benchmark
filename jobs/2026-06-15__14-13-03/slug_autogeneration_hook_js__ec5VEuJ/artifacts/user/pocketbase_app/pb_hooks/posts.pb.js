/// <reference path="../pb_data/types.d.ts" />

/**
 * Converts a string into a URL-friendly slug.
 * @param {string} str
 * @returns {string}
 */
function slugify(str) {
  return str
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[\s_]+/g, "-")      // replace spaces and underscores with hyphens
    .replace(/[^\w-]+/g, "")      // remove all non-word chars except hyphens
    .replace(/--+/g, "-")         // collapse multiple hyphens into one
    .replace(/^-+|-+$/g, "");     // strip leading and trailing hyphens
}

onRecordCreateRequest((e) => {
  const title = e.record.get("title");

  if (!title || title.trim() === "") {
    throw new BadRequestError("Title cannot be empty");
  }

  e.record.set("slug", slugify(title));

  e.next();
}, "posts");
