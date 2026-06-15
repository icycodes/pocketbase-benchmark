#!/bin/bash
# Default startup script: serves the stock PocketBase v0.31.0 binary on :8090.
# The executor is expected to overwrite this file so that the started server
# enforces the per-IP signup rate limit described in instruction.md.
cd /home/user/myproject
exec /home/user/myproject/pocketbase serve --http=0.0.0.0:8090
