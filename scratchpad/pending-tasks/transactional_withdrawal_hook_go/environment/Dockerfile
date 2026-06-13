FROM ubuntu:24.04

# --- System dependencies + Go toolchain + Python verification deps ---
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    curl -fsSL https://go.dev/dl/go1.23.4.linux-amd64.tar.gz -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm -f /tmp/go.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV GOCACHE="/root/.cache/go-build"

# --- Home directory ---
RUN mkdir -p /home/user && chmod 0755 /home/user

# --- Project skeleton at /home/user/myproject ---
RUN mkdir -p /home/user/myproject/migrations

# go.mod (pins PocketBase v0.31.0)
RUN cat > /home/user/myproject/go.mod <<'EOF'
module myproject

go 1.23

require github.com/pocketbase/pocketbase v0.31.0
EOF

# Initial main.go that wires the migrations package and starts PocketBase.
# The agent will modify this file to add the transactional withdrawal hook.
RUN cat > /home/user/myproject/main.go <<'EOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"

	_ "myproject/migrations"
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
EOF

# Bundled migration: creates `wallets` and `withdrawals` collections with open API rules
RUN cat > /home/user/myproject/migrations/1700000000_init_wallet_schema.go <<'EOF'
package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"

	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		open := types.Pointer("")

		// --- wallets ---
		wallets := core.NewBaseCollection("wallets")
		wallets.Fields.Add(
			&core.TextField{Name: "owner", Required: true, Max: 200},
			&core.NumberField{Name: "balance"},
		)
		wallets.ListRule = open
		wallets.ViewRule = open
		wallets.CreateRule = open
		wallets.UpdateRule = open
		wallets.DeleteRule = open
		if err := app.Save(wallets); err != nil {
			return err
		}

		// --- withdrawals ---
		withdrawals := core.NewBaseCollection("withdrawals")
		withdrawals.Fields.Add(
			&core.RelationField{
				Name:         "wallet",
				Required:     true,
				CollectionId: wallets.Id,
				MaxSelect:    1,
			},
			&core.NumberField{Name: "amount"},
			&core.TextField{Name: "note", Max: 500},
		)
		withdrawals.ListRule = open
		withdrawals.ViewRule = open
		withdrawals.CreateRule = open
		withdrawals.UpdateRule = open
		withdrawals.DeleteRule = open
		return app.Save(withdrawals)
	}, func(app core.App) error {
		for _, name := range []string{"withdrawals", "wallets"} {
			collection, err := app.FindCollectionByNameOrId(name)
			if err != nil {
				continue
			}
			if err := app.Delete(collection); err != nil {
				return err
			}
		}
		return nil
	})
}
EOF

# Pre-fetch and verify the PocketBase Go module so the agent can build offline-friendly.
RUN cd /home/user/myproject && \
    go mod tidy && \
    go build -o /tmp/preflight . && \
    rm -f /tmp/preflight

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31 Go backend with wallets/withdrawals scaffolding for the transactional withdrawal hook task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt packages: curl, wget, ca-certificates, git, python3, python3-pip, python3-pytest, bash, ripgrep, unzip
#   - pip3 packages: pytest-json-ctrf, requests, pytest-xprocess
#   - Go 1.23.4 toolchain installed under /usr/local/go (symlinked into /usr/local/bin)
#   - /home/user/myproject: PocketBase Go backend scaffolding
#       * go.mod pinning github.com/pocketbase/pocketbase v0.31.0
#       * main.go that registers the migrate plugin and starts PocketBase
#       * migrations/1700000000_init_wallet_schema.go that provisions
#         the `wallets` and `withdrawals` collections (API rules open)
#   - go module cache pre-populated and a preflight build verified
