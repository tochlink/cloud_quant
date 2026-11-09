"""项目路径。所有运行时数据都在 data/（已加入 .gitignore），CSV 交付物在 output/。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("QTW_DATA_DIR", ROOT / "data"))
OUTPUT_DIR = Path(os.environ.get("QTW_OUTPUT_DIR", ROOT / "output"))
PAPER_DIR = DATA_DIR / "paper"
STATIC_DIR = ROOT / "static"


def ensure_dirs() -> None:
    for d in (DATA_DIR, OUTPUT_DIR, PAPER_DIR, OUTPUT_DIR / "backtest"):
        d.mkdir(parents=True, exist_ok=True)
