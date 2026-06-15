FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        build-essential unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go 1.23 toolchain for building the PocketBase v0.31.0 application.
RUN curl -fsSL https://go.dev/dl/go1.23.4.linux-amd64.tar.gz -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

ENV PATH=/usr/local/go/bin:/root/go/bin:${PATH}
ENV GOPATH=/root/go
ENV GOCACHE=/root/.cache/go-build

RUN mkdir -p /home/user && chmod 0755 /home/user

# Provision the starter PocketBase project at /home/user/myproject.
RUN mkdir -p /home/user/myproject/migrations && \
    cat >/home/user/myproject/go.mod <<'EOF'
module pbapp

go 1.23

require github.com/pocketbase/pocketbase v0.31.0
EOF

RUN cat >/home/user/myproject/main.go <<'EOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"

	_ "pbapp/migrations"
)

func main() {
	app := pocketbase.New()

	// TODO: Register PocketBase event hooks on the "articles" collection so that
	// on every record create and record update REST request the server
	// automatically computes the following fields and writes them onto the
	// record before it is saved:
	//
	//   - word_count            (int): number of whitespace-separated words
	//                                  in the submitted "content" field.
	//   - reading_time_minutes  (int): ceil(word_count / 200), where 0 words
	//                                  must yield 0 minutes.
	//
	// The computed values must overwrite any values supplied by the client
	// for word_count / reading_time_minutes. Don't forget to return e.Next()
	// from each hook handler so the chain continues and the record is saved.

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
EOF

RUN cat >/home/user/myproject/migrations/0001_create_articles.go <<'EOF'
package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		collection := core.NewBaseCollection("articles")

		collection.Fields.Add(
			&core.TextField{Name: "title", Required: true, Max: 200},
			&core.TextField{Name: "content"},
			&core.NumberField{Name: "word_count", OnlyInt: true},
			&core.NumberField{Name: "reading_time_minutes", OnlyInt: true},
		)

		return app.Save(collection)
	}, func(app core.App) error {
		c, err := app.FindCollectionByNameOrId("articles")
		if err != nil {
			return err
		}
		return app.Delete(c)
	})
}
EOF

# Pre-resolve the Go module graph so the agent can build without network access
# and so `go list -m` works in the initial state check.
RUN cd /home/user/myproject && \
    go mod tidy

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go starter project with an articles collection migration; the agent must implement word_count / reading_time_minutes hooks."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - pip3 verification deps: requests, pytest-xprocess
#   - Go 1.23 toolchain at /usr/local/go (symlinked into /usr/local/bin)
#   - /home/user/myproject: PocketBase v0.31.0 starter project
#     - go.mod / go.sum: module "pbapp" pinning github.com/pocketbase/pocketbase v0.31.0
#     - main.go: starter entry point with TODO placeholders for the event hooks
#     - migrations/0001_create_articles.go: registers the "articles" collection
#       (title, content, word_count, reading_time_minutes)
