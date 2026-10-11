#!/usr/bin/env sh
# Start the local demo on macOS or Linux. Works with Docker Desktop, OrbStack, Colima, Rancher or Podman.
set -eu
cd "$(dirname "$0")/.."
PORT="${FOUNDRY_PORT:-8000}"
if command -v docker >/dev/null 2>&1; then ENGINE=docker
elif command -v podman >/dev/null 2>&1; then ENGINE=podman
else echo "Install Docker Desktop (https://docs.docker.com/desktop/) or Podman (https://podman.io) first." >&2; exit 1; fi
echo "Using $ENGINE. Building and starting the Policy Foundry on http://localhost:$PORT ..."
$ENGINE compose up --build -d
i=0; until curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; do i=$((i+1)); [ $i -gt 60 ] && { echo "Timed out. Check: $ENGINE compose logs" >&2; exit 1; }; sleep 1; done
echo "Ready: http://localhost:$PORT   (stop with: $ENGINE compose down)"
case "$(uname -s)" in Darwin) open "http://localhost:$PORT" ;; Linux) command -v xdg-open >/dev/null && xdg-open "http://localhost:$PORT" >/dev/null 2>&1 || true ;; esac
