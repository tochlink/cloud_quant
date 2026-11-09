#!/usr/bin/env bash
# 一键启动：自动创建虚拟环境、安装依赖，并在 http://127.0.0.1:8787 提供页面。
# 若端口上 /api/health 已 ok，则直接退出 0（幂等，避免 Address already in use）。
set -euo pipefail
cd "$(dirname "$0")"
PORT="${QTW_PORT:-8787}"
HOST="${QTW_HOST:-127.0.0.1}"
HEALTH_URL="http://${HOST}:${PORT}/api/health"

if curl -fsS -m 2 "${HEALTH_URL}" 2>/dev/null | grep -q '"ok"[[:space:]]*:[[:space:]]*true'; then
  echo "================================================================"
  echo "  QTW 已在运行： ${HEALTH_URL}"
  echo "  （幂等跳过，未再次绑定端口）"
  if [ "${QTW_ALLOW_LIVE_ORDERS:-0}" = "1" ]; then
    echo "  ⚠️  当前环境 QTW_ALLOW_LIVE_ORDERS=1"
  fi
  echo "================================================================"
  exit 0
fi

if [ ! -x .venv/bin/python ]; then
  echo "首次运行：创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import fastapi, uvicorn, pandas, cryptography, yaml" 2>/dev/null; then
  echo "安装依赖 ..."
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi
mkdir -p data output
chmod 700 data
echo "================================================================"
echo "  QTW 量化交易控制台（默认纸面模式，不下真实订单）"
echo "  打开： http://${HOST}:${PORT}"
if [ "${QTW_ALLOW_LIVE_ORDERS:-0}" = "1" ]; then
  echo "  ⚠️  已设置 QTW_ALLOW_LIVE_ORDERS=1：若页面中也开启实盘，将发送真实订单！"
fi
echo "================================================================"
exec .venv/bin/python -m qtw serve --host "${HOST}" --port "${PORT}"
