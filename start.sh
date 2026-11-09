#!/usr/bin/env bash
# 一键启动：自动创建虚拟环境、安装依赖，并在 http://127.0.0.1:8787 提供页面。
set -euo pipefail
cd "$(dirname "$0")"
PORT="${QTW_PORT:-8787}"
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
echo "  打开： http://127.0.0.1:${PORT}"
if [ "${QTW_ALLOW_LIVE_ORDERS:-0}" = "1" ]; then
  echo "  ⚠️  已设置 QTW_ALLOW_LIVE_ORDERS=1：若页面中也开启实盘，将发送真实订单！"
fi
echo "================================================================"
exec .venv/bin/python -m qtw serve --host 127.0.0.1 --port "${PORT}"
