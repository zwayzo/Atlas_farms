#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$project_root/backend"
frontend_dir="$project_root/frontend"
backend_python="$backend_dir/.venv/bin/python"

if ! command -v python3.12 >/dev/null 2>&1; then
  echo 'Python 3.12 is required. Install it and run ./start.sh again.' >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo 'Node.js and npm are required. Install them and run ./start.sh again.' >&2
  exit 1
fi

if [[ ! -x "$backend_python" ]] || ! "$backend_python" -c 'import sys; assert sys.version_info[:2] == (3, 12)' >/dev/null 2>&1; then
  echo 'Creating the Python 3.12 environment...'
  python3.12 -m venv --clear "$backend_dir/.venv"
fi

if ! "$backend_python" -c 'import fastapi, uvicorn, pandas, numpy, openpyxl, dotenv, multipart, groq, pytest, httpx' >/dev/null 2>&1; then
  echo 'Installing backend dependencies...'
  "$backend_python" -m pip install -r "$backend_dir/app/requirements.txt"
fi

if [[ ! -x "$frontend_dir/node_modules/.bin/vite" ]]; then
  echo 'Installing frontend dependencies...'
  (cd "$frontend_dir" && npm ci)
fi

if [[ ! -f "$backend_dir/.env" ]]; then
  cp "$backend_dir/.env.example" "$backend_dir/.env"
  echo 'Created backend/.env. The Groq key is optional; the app works without it.'
fi

if ! "$backend_python" -c 'import socket, sys; sock = socket.socket(); sock.settimeout(0.2); sys.exit(sock.connect_ex(("127.0.0.1", 8000)) == 0)' ; then
  echo 'Port 8000 is already in use. Stop the existing backend and run ./start.sh again.' >&2
  exit 1
fi

backend_pid=''
cleanup() {
  if [[ -n "$backend_pid" ]]; then
    kill "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

(cd "$backend_dir" && exec "$backend_python" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
backend_pid=$!

for ((attempt = 0; attempt < 60; attempt++)); do
  if curl --silent --fail http://127.0.0.1:8000/openapi.json >/dev/null; then
    break
  fi
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    echo 'The backend failed to start. Check the error above.' >&2
    exit 1
  fi
  sleep 0.25
done
if ! curl --silent --fail http://127.0.0.1:8000/openapi.json >/dev/null; then
  echo 'The backend did not become ready on port 8000.' >&2
  exit 1
fi

echo 'Backend ready. Open http://127.0.0.1:5173 after Vite starts. Ctrl+C stops both servers.'
(cd "$frontend_dir" && npm run dev -- --host 127.0.0.1 --strictPort)
