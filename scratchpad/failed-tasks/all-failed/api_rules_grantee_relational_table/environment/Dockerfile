FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Setup PocketBase standalone in /home/user/myproject
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    rm pocketbase.zip && \
    chmod +x pocketbase

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase standalone v0.31.0 environment for API rules testing."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - /home/user/myproject: PocketBase project directory with the pocketbase binary
