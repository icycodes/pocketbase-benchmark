FROM ubuntu:24.04

# Base OS packages and Python tooling required by the harbor pytest harness.
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go (needed to build & run the PocketBase project via `go run`).
ENV GO_VERSION=1.23.4
RUN curl -fsSL https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

ENV GOPATH=/root/go
ENV PATH=/usr/local/go/bin:/root/go/bin:$PATH

ENV POCKETBASE_SUPERUSER_EMAIL=admin@example.com
ENV POCKETBASE_SUPERUSER_PASSWORD=SuperSecret123!

# Convenience: also ship the standalone PocketBase v0.31.0 binary for ad-hoc
# inspection (`pocketbase` in PATH). The project itself is built from source.
RUN curl -fsSL -o /tmp/pb.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip /tmp/pb.zip -d /usr/local/bin/ && \
    rm /tmp/pb.zip && \
    chmod +x /usr/local/bin/pocketbase

RUN mkdir -p /home/user && chmod 0755 /home/user

# Bootstrap the PocketBase Go project.
RUN mkdir -p /home/user/myproject/migrations

RUN cat > /home/user/myproject/go.mod <<'GOMODEOF'
module myapp

go 1.23

require github.com/pocketbase/pocketbase v0.31.0
GOMODEOF

RUN cat > /home/user/myproject/main.go <<'MAINEOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	_ "myapp/migrations"
)

func main() {
	app := pocketbase.New()

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
MAINEOF

RUN cat > /home/user/myproject/migrations/1700000000_init.go <<'MIGEOF'
package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// Create the `users` auth collection.
		users := core.NewAuthCollection("users")
		if err := app.Save(users); err != nil {
			return err
		}

		// Create the `posts` base collection that references `users` via the
		// `author` relation field.
		posts := core.NewBaseCollection("posts")
		posts.Fields.Add(
			&core.TextField{Name: "title", Required: true, Max: 200},
			&core.RelationField{
				Name:         "author",
				Required:     true,
				MaxSelect:    1,
				CollectionId: users.Id,
			},
			&core.AutodateField{Name: "created", OnCreate: true},
			&core.AutodateField{Name: "updated", OnCreate: true, OnUpdate: true},
		)

		return app.Save(posts)
	}, func(app core.App) error {
		if c, err := app.FindCollectionByNameOrId("posts"); err == nil {
			if err := app.Delete(c); err != nil {
				return err
			}
		}
		if c, err := app.FindCollectionByNameOrId("users"); err == nil {
			if err := app.Delete(c); err != nil {
				return err
			}
		}
		return nil
	})
}
MIGEOF

# Pre-download Go modules and pre-build the project so the first invocation of
# `go run . serve` inside the container is fast (modules + build cache are
# already populated and `go.sum` is generated).
RUN cd /home/user/myproject && \
    go mod tidy && \
    go build -o /tmp/myapp-warmup . && \
    rm /tmp/myapp-warmup

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go project pre-seeded with users/posts collections for the user_post_stats view collection task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - extra apt packages: unzip procps (for pkill in the verifier and unzipping PB)
#   - always required pip3 packages: pytest-json-ctrf
#   - pip3 packages for tests: requests, pytest-xprocess
#   - Go 1.23.4 toolchain at /usr/local/go (linked to /usr/local/bin/go)
#   - PocketBase v0.31.0 standalone binary at /usr/local/bin/pocketbase (handy CLI)
#   - /home/user/myproject: PocketBase Go project (main.go + go.mod + migrations/1700000000_init.go)
#     that creates the initial `users` auth collection and `posts` base collection.
#   - Pre-warmed Go module + build cache so `go run . serve` starts quickly.
