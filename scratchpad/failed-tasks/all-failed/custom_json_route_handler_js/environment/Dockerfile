FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/myproject/pb_hooks && \
    cd /home/user/myproject && \
    LATEST_PB=$(curl -s https://api.github.com/repos/pocketbase/pocketbase/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | tr -d v) && \
    curl -fsSL -o pb.zip "https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_${LATEST_PB}_linux_amd64.zip" && \
    unzip pb.zip && \
    rm pb.zip && \
    chmod +x pocketbase

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with latest PocketBase binary and python testing dependencies."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - PocketBase binary installed in /home/user/myproject
#   - /home/user/myproject: project directory
#   - /home/user/myproject/pb_hooks: directory for custom JS hooks
