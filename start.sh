#!/bin/bash
# UNSCRIPTED launcher.
# Needs: Node 22+, python3, and a logged-in `claude` CLI (https://claude.com/claude-code).
#
#   ./start.sh                    # run the show
#   FABLE_MODEL=claude-sonnet-5 ./start.sh  # use a different model
#   PORT=9000 ./start.sh                    # use a different port
set -euo pipefail
cd "$(dirname "$0")"

export PORT="${PORT:-8787}"
export FABLE_MODEL="${FABLE_MODEL:-claude-opus-5}"      # any model your `claude` CLI can run
export FABLE_EFFORT="${FABLE_EFFORT:-high}"             # effort for planning turns
export FABLE_EFFORT_BG="${FABLE_EFFORT_BG:-medium}"     # effort for background turns
export UNSCRIPTED_KEY="${UNSCRIPTED_KEY:-$(node -e 'console.log(require("crypto").randomBytes(8).toString("hex"))')}"

command -v node >/dev/null || { echo "node 22+ is required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v claude >/dev/null || { echo "the claude CLI is required and must be logged in"; exit 1; }

# Stop a previous copy of THIS install only.
pkill -f "node $PWD/server.js" 2>/dev/null || true
sleep 0.3

node "$PWD/server.js" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT INT TERM
sleep 1

# The stage screen is public: put it on the projector and make it fullscreen.
open "http://localhost:$PORT/" 2>/dev/null || true

wait $SERVER_PID
