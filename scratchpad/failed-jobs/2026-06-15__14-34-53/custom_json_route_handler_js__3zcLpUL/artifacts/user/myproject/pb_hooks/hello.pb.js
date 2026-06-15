routerAdd("GET", "/api/myapp/hello/{name}", (e) => {
    let name = e.request.pathValue("name");
    return e.json(200, {
        "message": "Hello, " + name + "!"
    });
});
