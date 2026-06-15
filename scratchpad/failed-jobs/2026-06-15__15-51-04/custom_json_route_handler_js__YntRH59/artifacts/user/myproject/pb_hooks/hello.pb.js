// Custom greeting endpoint: GET /api/myapp/hello/{name}
routerAdd("GET", "/api/myapp/hello/{name}", function (e) {
    var name = e.request.pathValue("name");
    e.json(200, { "message": "Hello, " + name + "!" });
});
