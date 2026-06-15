FROM ubuntu:24.04

ENV GO_VERSION=1.23.4
ENV MAILPIT_VERSION=v1.20.6
ENV PATH=/usr/local/go/bin:/root/go/bin:${PATH}
ENV GOPATH=/root/go
ENV GOCACHE=/root/.cache/go-build

ENV TEST_USER_EMAIL=alice@example.com
ENV TEST_USER_NAME=Alice
ENV TEST_USER_PASSWORD=TestSecret123!
ENV SUPERUSER_EMAIL=admin@example.com
ENV SUPERUSER_PASSWORD=SuperSecret123!


RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip tar build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf \
        pytest-xprocess \
        requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go toolchain.
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tgz && \
    tar -C /usr/local -xzf /tmp/go.tgz && \
    rm /tmp/go.tgz && \
    /usr/local/go/bin/go version

# Install Mailpit (SMTP capture server with HTTP UI/API).
RUN curl -fsSL "https://github.com/axllent/mailpit/releases/download/${MAILPIT_VERSION}/mailpit-linux-amd64.tar.gz" -o /tmp/mailpit.tgz && \
    tar -xzf /tmp/mailpit.tgz -C /tmp && \
    mv /tmp/mailpit /usr/local/bin/mailpit && \
    chmod +x /usr/local/bin/mailpit && \
    rm -f /tmp/mailpit.tgz && \
    mailpit version

# Warm the Go module cache with PocketBase v0.31.0 so the task does not require
# rebuilding the full dependency graph from scratch.
RUN mkdir -p /opt/pb-cache && \
    cd /opt/pb-cache && \
    /usr/local/go/bin/go mod init pbcache && \
    /usr/local/go/bin/go get github.com/pocketbase/pocketbase@v0.31.0 && \
    /usr/local/go/bin/go mod tidy

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/myapp && chmod 0755 /home/user/myapp

LABEL Author="generate-harbor-tasks"
LABEL Description="Go + PocketBase v0.31.0 + Mailpit environment for the mailer_password_reset_override_go task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: pytest-xprocess, requests (used by initial and final state tests)
#   - Go 1.23.4 toolchain installed at /usr/local/go
#   - Mailpit v1.20.6 installed at /usr/local/bin/mailpit (started by test_initial_state.py)
#   - PocketBase v0.31.0 Go module pre-fetched into the module cache via /opt/pb-cache
#   - /home/user/myapp: empty project directory where the agent will build the Go PocketBase app
