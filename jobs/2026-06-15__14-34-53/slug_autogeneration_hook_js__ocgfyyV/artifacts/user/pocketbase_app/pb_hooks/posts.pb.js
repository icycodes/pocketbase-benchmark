// pb_hooks/posts.pb.js
onRecordCreateRequest((e) => {
    const title = e.record.get("title");
    
    if (!title) {
        throw new BadRequestError("Title cannot be empty");
    }
    
    // Polyfill for $String.slugify if it doesn't exist
    const slugify = typeof $String !== 'undefined' && $String.slugify 
        ? $String.slugify 
        : (str) => {
            return str.toString().toLowerCase().trim()
                .replace(/\s+/g, '-')
                .replace(/[^\w\-]+/g, '')
                .replace(/\-\-+/g, '-');
        };
        
    e.record.set("slug", slugify(title));
    
    e.next();
}, "posts");
