FROM ubuntu:24.04

# Base OS toolchain, Python, and required pip dependencies for the verifier.
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        build-essential xz-utils unzip jq && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf \
        pytest-xprocess \
        requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install the Go toolchain (PocketBase v0.31.0 requires Go 1.24+).
RUN curl -fsSL -o /tmp/go.tar.gz https://go.dev/dl/go1.24.4.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm -f /tmp/go.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV GOBIN="/root/go/bin"

# Standard user directory.
RUN mkdir -p /home/user && chmod 0755 /home/user

# Seed the initial PocketBase Go project at /home/user/myproject.
RUN mkdir -p /home/user/myproject/migrations
RUN cat > /home/user/myproject/go.mod <<'EOF'
module articles-app

go 1.24

require github.com/pocketbase/pocketbase v0.31.0
EOF

RUN cat > /home/user/myproject/main.go <<'EOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	// Register the local migrations package (creates the "articles" collection).
	_ "articles-app/migrations"
)

func main() {
	app := pocketbase.New()

	// Apply pending migrations automatically on `serve`.
	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	// TODO: register the OnRecordCreateRequest("articles") hook here so that
	// every successful article creation request receives an auto-generated slug
	// and every empty/whitespace-only title is rejected with a 400 response.

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
EOF

RUN cat > /home/user/myproject/migrations/1700000000_init_articles.go <<'EOF'
package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

func init() {
	m.Register(func(app core.App) error {
		collection := core.NewBaseCollection("articles")

		// Open rules so the verifier can exercise the public REST API without auth.
		collection.ListRule = types.Pointer("")
		collection.ViewRule = types.Pointer("")
		collection.CreateRule = types.Pointer("")
		collection.UpdateRule = types.Pointer("")
		collection.DeleteRule = types.Pointer("")

		collection.Fields.Add(
			&core.TextField{Name: "title", Required: true},
			&core.TextField{Name: "slug"},
			&core.TextField{Name: "content"},
		)

		return app.Save(collection)
	}, func(app core.App) error {
		collection, err := app.FindCollectionByNameOrId("articles")
		if err != nil {
			return err
		}
		return app.Delete(collection)
	})
}
EOF

# Pre-fetch the Go module cache and verify the skeleton builds cleanly so
# `test_initial_state.py` can run `go build` offline during evaluation.
RUN cd /home/user/myproject && \
    go mod tidy && \
    go build -o /tmp/articles-app-bootstrap . && \
    rm -f /tmp/articles-app-bootstrap

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go project skeleton with a pre-registered 'articles' collection migration; the executor must add an OnRecordCreateRequest slug-generation hook."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - extras for Go builds: build-essential xz-utils unzip jq
#   - always required pip3 packages: pytest-json-ctrf, plus pytest-xprocess + requests for the verifier
#   - Go 1.24 toolchain at /usr/local/go (PocketBase v0.31.0 requires Go 1.24+)
#   - /home/user/myproject: PocketBase Go project skeleton
#     - go.mod / go.sum: module `articles-app` with github.com/pocketbase/pocketbase v0.31.0
#     - main.go: minimal entrypoint with migratecmd registered, slug hook intentionally missing
#     - migrations/1700000000_init_articles.go: Go migration creating the `articles` base collection
#       (fields: title required text, slug text, content text; all API rules open)
#   - Go module cache pre-populated; skeleton builds cleanly with `go build .` offline
