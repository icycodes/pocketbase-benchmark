routerAdd("GET", "/api/myapp/hello/{name}", (e) => {
  const name = e.request.pathValue("name");
  e.json(200, { message: "Hello, " + name + "!" });
});