FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip imagemagick && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /usr/local/bin/ && \
    rm pocketbase.zip && \
    chmod +x /usr/local/bin/pocketbase && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user/pb-task && \
    convert -size 200x200 xc:red /home/user/pb-task/input.jpg && \
    chmod 0755 /home/user/pb-task && \
    chmod 0644 /home/user/pb-task/input.jpg

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with Node.js v24 and PocketBase v0.31.0 installed."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - unzip and imagemagick for downloading pocketbase and generating sample image
#   - Node.js v24 for the task execution
#   - PocketBase v0.31.0 installed in /usr/local/bin/pocketbase
#   - /home/user/pb-task: project directory
#   - /home/user/pb-task/input.jpg: sample 200x200 JPEG image
