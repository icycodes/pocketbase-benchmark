onRecordBeforeCreateRequest((e) => {
    const title = e.record.get("title");

    if (!title || title.trim() === "") {
        throw new BadRequestError("Title cannot be empty");
    }

    const slug = $String.slugify(title);
    e.record.set("slug", slug);
}, "posts");