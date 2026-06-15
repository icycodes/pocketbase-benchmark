FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/pocketbase && \
    rm pocketbase.zip && \
    wget https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-x64-release.zip && \
    unzip dartsdk-linux-x64-release.zip -d /usr/local/ && \
    ln -s /usr/local/dart-sdk/bin/dart /usr/local/bin/dart && \
    rm dartsdk-linux-x64-release.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    cat >pubspec.yaml <<'EOF'
name: myproject
description: A starting point for Dart libraries or applications.
version: 1.0.0

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  pocketbase: ^0.22.0
EOF

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with Dart SDK and PocketBase v0.31.0."

# Start pocketbase in the background
CMD ["/bin/bash", "-c", "pocketbase serve --http=0.0.0.0:8090 --dir=/home/user/pb_data & trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - pocketbase v0.31.0 installed in /usr/local/bin
#   - Dart SDK installed in /usr/local/dart-sdk
#   - /home/user/myproject: Dart project directory with pubspec.yaml
