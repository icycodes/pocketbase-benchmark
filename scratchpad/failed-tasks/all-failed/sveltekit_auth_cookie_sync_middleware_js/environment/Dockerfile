FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase v0.31.0
RUN curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /usr/local/bin && \
    rm pocketbase.zip && \
    chmod +x /usr/local/bin/pocketbase

RUN mkdir -p /home/user && chmod 0755 /home/user

# Setup SvelteKit project skeleton
RUN mkdir -p /home/user/sveltekit-app/src/routes && \
    cd /home/user/sveltekit-app && \
    cat > package.json <<'EOF'
{
  "name": "sveltekit-app",
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@sveltejs/adapter-auto": "^3.0.0",
    "@sveltejs/kit": "^2.0.0",
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "svelte": "^4.2.7",
    "vite": "^5.0.3"
  },
  "dependencies": {
    "pocketbase": "^0.21.0"
  }
}
EOF
RUN cd /home/user/sveltekit-app && \
    cat > svelte.config.js <<'EOF'
import adapter from '@sveltejs/adapter-auto';

const config = {
	kit: {
		adapter: adapter()
	}
};

export default config;
EOF
RUN cd /home/user/sveltekit-app && \
    cat > vite.config.js <<'EOF'
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()]
});
EOF
RUN cd /home/user/sveltekit-app && \
    cat > src/app.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8" />
		<link rel="icon" href="%sveltekit.assets%/favicon.png" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		%sveltekit.head%
	</head>
	<body data-sveltekit-preload-data="hover">
		<div style="display: contents">%sveltekit.body%</div>
	</body>
</html>
EOF
RUN cd /home/user/sveltekit-app && \
    cat > src/routes/+page.svelte <<'EOF'
<h1>Hello PocketBase</h1>
EOF
RUN cd /home/user/sveltekit-app && npm install

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 and SvelteKit environment for implementing auth cookie sync middleware."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - Node.js v24 installed
#   - PocketBase v0.31.0 installed in /usr/local/bin
#   - /home/user/sveltekit-app: SvelteKit project skeleton with pocketbase SDK installed
