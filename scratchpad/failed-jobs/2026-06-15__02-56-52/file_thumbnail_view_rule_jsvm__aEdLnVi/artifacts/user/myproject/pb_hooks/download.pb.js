onFileDownloadRequest((e) => {
    console.log("Hook triggered!");
    if (e.collection.name === "photos") {
        const thumb = e.httpContext.queryParam("thumb");
        if (thumb && thumb !== "100x100" && thumb !== "400x300t") {
            return e.httpContext.json(400, {message: "unsupported thumb"});
        }
    }
})
