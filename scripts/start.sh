#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
port="${1:-8000}"
if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
  echo "端口必须在 1–65535 之间。" >&2
  exit 2
fi
command -v uv >/dev/null || { echo "请安装 uv 和 Python 3.12+。" >&2; exit 1; }
command -v npm >/dev/null || { echo "请安装 Node.js 22.12+。" >&2; exit 1; }
(cd "$root/frontend" && npm ci && npm run build)
(cd "$root/backend" && uv sync --locked && echo "NetCase: http://127.0.0.1:$port" &&
  uv run --no-sync uvicorn app.main:create_app --factory --host 127.0.0.1 --port "$port" --no-access-log)
