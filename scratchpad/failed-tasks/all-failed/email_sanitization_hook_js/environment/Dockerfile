FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pocketbase && \
    cd /home/user/pocketbase && \
    curl -fsSL https://github.com/pocketbase/pocketbase/releases/download/v0.23.0/pocketbase_0.23.0_linux_amd64.zip -o pb.zip && \
    unzip pb.zip && \
    rm pb.zip && \
    chmod +x pocketbase

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with PocketBase v0.23.0 installed."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - unzip for downloading PocketBase
#   - always required pip3 packages: pytest-json-ctrf
#   - python dependencies for verification: requests pytest-xprocess
#   - PocketBase v0.23.0 binary at /home/user/pocketbase/pocketbase