"""命令行：python -m qtw serve | backtest | cycle | signals"""
from __future__ import annotations

import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser(prog="qtw")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default=os.environ.get("QTW_HOST", "127.0.0.1"))
    sv.add_argument("--port", type=int, default=int(os.environ.get("QTW_PORT", 8787)))
    bt = sub.add_parser("backtest")
    bt.add_argument("--venue", choices=["okx", "gate"])
    bt.add_argument("--bars", type=int, default=1500)
    sub.add_parser("cycle")
    sub.add_parser("signals")
    a = ap.parse_args()
    if a.cmd == "serve":
        import uvicorn
        print(f"\n  QTW 量化交易控制台： http://{a.host}:{a.port}\n")
        uvicorn.run("qtw.app:app", host=a.host, port=a.port, log_level="info")
        return
    from fastapi.testclient import TestClient

    from qtw.app import app
    c = TestClient(app)
    if a.cmd == "backtest":
        body = {"bars": a.bars, **({"venue": a.venue} if a.venue else {})}
        r = c.post("/api/backtest", json=body).json()
        print(json.dumps(r.get("summary", r), ensure_ascii=False, indent=2))
    elif a.cmd == "cycle":
        print(json.dumps(c.post("/api/cycle").json(), ensure_ascii=False, indent=2))
    else:
        r = c.get("/api/signals").json()
        for x in r["rows"]:
            print(x["symbol"], x.get("advice"), x.get("market_cn"), x.get("ref_price"), x.get("error", ""))


if __name__ == "__main__":
    main()
