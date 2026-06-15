routerAdd("GET", "/api/myapp/hello/{name}", function (e) {
    var name = e.request.pathValue("name");
    return e.json(200, { message: "Hello, " + name + "!" });
});
