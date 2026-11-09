#!/usr/bin/env bash
# Idempotent keep-alive for the 24/7 polish routine:
# if /api/health is already ok, exit 0; otherwise start QTW in the background
# (nohup + data/server.log + data/qtw.pid). Never enables live orders by itself.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${QTW_PORT:-8787}"
HOST="${QTW_HOST:-127.0.0.1}"
PIDFILE="data/qtw.pid"
LOGFILE="data/server.log"
HEALTH_URL="http://${HOST}:${PORT}/api/health"

mkdir -p data output
chmod 700 data

# Force live-off unless the operator explicitly exported ALLOW=1 already.
export QTW_ALLOW_LIVE_ORDERS="${QTW_ALLOW_LIVE_ORDERS:-0}"

healthy() {
  local body
  body="$(curl -fsS -m 3 "${HEALTH_URL}" 2>/dev/null || true)"
  [[ -n "${body}" ]] && grep -q '"ok"[[:space:]]*:[[:space:]]*true' <<<"${body}"
}

print_health() {
  curl -fsS -m 3 "${HEALTH_URL}" 2>/dev/null || true
  echo
}

if healthy; then
  echo "QTW already up · http://${HOST}:${PORT}"
  print_health
  exit 0
fi

if [[ -f "${PIDFILE}" ]]; then
  old="$(cat "${PIDFILE}" 2>/dev/null || true)"
  if [[ -n "${old}" ]] && kill -0 "${old}" 2>/dev/null; then
    echo "PID ${old} is alive but ${HEALTH_URL} is not healthy yet; waiting…"
    for _ in $(seq 1 20); do
      sleep 1
      if healthy; then
        echo "QTW became healthy · http://${HOST}:${PORT}"
        print_health
        exit 0
      fi
    done
    echo "Stale/unhealthy process ${old}; refusing to start a second copy." >&2
    echo "Inspect ${LOGFILE}, then: kill ${old} && rm -f ${PIDFILE}" >&2
    exit 1
  fi
  rm -f "${PIDFILE}"
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "首次运行：创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import fastapi, uvicorn, pandas, cryptography, yaml" 2>/dev/null; then
  echo "安装依赖 ..."
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

echo "Starting QTW on ${HOST}:${PORT} (live orders env=${QTW_ALLOW_LIVE_ORDERS}) …"
# start.sh exec's into uvicorn, so the background PID becomes the server PID.
nohup env QTW_ALLOW_LIVE_ORDERS="${QTW_ALLOW_LIVE_ORDERS}" \
  QTW_PORT="${PORT}" QTW_HOST="${HOST}" \
  ./start.sh >>"${LOGFILE}" 2>&1 &
echo $! >"${PIDFILE}"

for _ in $(seq 1 40); do
  sleep 1
  if healthy; then
    echo "QTW started · http://${HOST}:${PORT} · pid $(cat "${PIDFILE}")"
    print_health
    exit 0
  fi
done

echo "QTW failed to become healthy within 40s. See ${LOGFILE}" >&2
exit 1
