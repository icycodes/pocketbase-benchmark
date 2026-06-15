// pb_hooks/posts.pb.js

onRecordCreateRequest((e) => {
    // Define $String wrapper inside the handler because PocketBase serializes and executes
    // each handler in an isolated context.
    const $String = {
        slugify: function(text) {
            if (!text) return "";
            return text
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, "-")
                .replace(/^-|-$/g, "");
        }
    };

    const title = e.record.get("title");
    if (!title || String(title).trim() === "") {
        throw new BadRequestError("Title cannot be empty");
    }

    // Programmatically generate slug using $String.slugify()
    const slug = $String.slugify(title);
    e.record.set("slug", slug);

    return e.next();
}, "posts");
