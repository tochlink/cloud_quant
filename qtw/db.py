"""SQLite 数据库（标准库 sqlite3，WAL 模式）。

文件：data/qtw.sqlite（data/ 已在 .gitignore）。
存放：真实公共 K 线缓存、纸面账本（持仓 / 成交 / 账本快照 / 止损锁 / 停止自动）、订单路由日志、
回测运行记录、非敏感配置。**绝不存放 API Key / Secret / Passphrase**（它们只在加密的 data/secrets.enc 中）。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .paths import DATA_DIR, ensure_dirs

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);

-- 只缓存从官方公共 REST 拉到的真实 K 线；不插值、不补洞
CREATE TABLE IF NOT EXISTS candles (
  venue TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL, interval TEXT NOT NULL,
  open_time INTEGER NOT NULL,            -- 毫秒 UTC
  open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, volume REAL,
  data_source TEXT NOT NULL,             -- okx_public_rest / gate_public_rest
  source_host TEXT NOT NULL, fetched_at TEXT NOT NULL,
  PRIMARY KEY (venue, market, symbol, interval, open_time)
);

CREATE TABLE IF NOT EXISTS paper_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS paper_positions (
  symbol TEXT PRIMARY KEY, market TEXT NOT NULL, side TEXT NOT NULL, qty REAL NOT NULL,
  entry_price REAL NOT NULL, entry_time TEXT NOT NULL, stop_price REAL NOT NULL,
  mark_price REAL NOT NULL, mark_time TEXT NOT NULL, notional_entry REAL NOT NULL,
  fees_paid REAL NOT NULL, signal_bar TEXT NOT NULL, venue TEXT DEFAULT '', mark_source TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS paper_blocks (symbol TEXT PRIMARY KEY, blocked_signal INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS paper_halts (symbol TEXT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS paper_fills (
  fill_id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, symbol TEXT NOT NULL, market TEXT NOT NULL,
  side TEXT NOT NULL, action TEXT NOT NULL, qty REAL NOT NULL, price REAL NOT NULL, price_kind TEXT NOT NULL,
  notional_usdt REAL NOT NULL, fee_usdt REAL NOT NULL, realized_pnl_usdt REAL NOT NULL, reason TEXT,
  mode TEXT NOT NULL, venue TEXT NOT NULL, data_source TEXT DEFAULT '', price_time TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS paper_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, equity_usdt REAL NOT NULL, realized_usdt REAL NOT NULL,
  unrealized_usdt REAL NOT NULL, cash_free_usdt REAL NOT NULL, gross_exposure_usdt REAL NOT NULL,
  net_exposure_usdt REAL NOT NULL, positions INTEGER NOT NULL, note TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, mode TEXT NOT NULL, venue TEXT NOT NULL,
  symbol TEXT NOT NULL, market TEXT NOT NULL, action TEXT NOT NULL, qty REAL, ref_price REAL,
  status TEXT NOT NULL, detail TEXT
);

CREATE TABLE IF NOT EXISTS backtest_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, venue TEXT NOT NULL,
  data_source TEXT NOT NULL, fetched_at TEXT, params TEXT NOT NULL, summary TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS backtest_equity (
  run_id INTEGER NOT NULL, time TEXT NOT NULL, equity REAL, drawdown REAL, gross_exposure REAL,
  net_exposure REAL, positions INTEGER, PRIMARY KEY (run_id, time)
);
CREATE TABLE IF NOT EXISTS backtest_trades (
  run_id INTEGER NOT NULL, seq INTEGER NOT NULL, symbol TEXT, market TEXT, side TEXT, entry_time TEXT,
  entry_price REAL, qty REAL, notional_usdt REAL, stop_price REAL, exit_time TEXT, exit_price REAL,
  exit_reason TEXT, pnl_usdt REAL, fees_usdt REAL, return_pct REAL, bars_held INTEGER, status TEXT,
  PRIMARY KEY (run_id, seq)
);
"""

_LOCK = threading.RLock()
_CONNS: dict[str, sqlite3.Connection] = {}


def db_path() -> Path:
    return DATA_DIR / "qtw.sqlite"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """每个数据库文件一个共享连接（加锁串行化写入）。"""
    p = str(path or db_path())
    with _LOCK:
        if p in _CONNS:
            return _CONNS[p]
        ensure_dirs()
        conn = sqlite3.connect(p, check_same_thread=False, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        _CONNS[p] = conn
        return conn


@contextmanager
def tx(conn: sqlite3.Connection | None = None):
    c = conn or connect()
    with _LOCK:
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise


def query(sql: str, args: tuple = (), conn=None) -> list[dict]:
    c = conn or connect()
    with _LOCK:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def execute(sql: str, args: tuple = (), conn=None) -> int:
    c = conn or connect()
    with _LOCK:
        cur = c.execute(sql, args)
        return cur.lastrowid


def meta_get(key: str, conn=None) -> str | None:
    r = query("SELECT value FROM meta WHERE key=?", (key,), conn)
    return r[0]["value"] if r else None


def meta_set(key: str, value: str, conn=None) -> None:
    execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value), conn)


def counts(conn=None) -> dict:
    out = {}
    for t in ("candles", "paper_positions", "paper_fills", "paper_ledger", "orders", "backtest_runs",
              "backtest_equity", "backtest_trades", "settings"):
        out[t] = query(f"SELECT COUNT(*) n FROM {t}", (), conn)[0]["n"]
    return out


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, default=str)


def checkpoint_wal(mode: str = "PASSIVE") -> tuple[int, int, int]:
    """Move durable WAL frames into the main DB without blocking readers.

    PASSIVE never waits on other readers or writers (it may no-op if the WAL
    is busy). TRUNCATE also shrinks the on-disk ``-wal`` file to 0 when idle —
    PASSIVE alone can leave a multi-MB empty WAL after heavy candle writes.
    Returns sqlite's (busy, log, checkpointed) triple.
    """
    if mode not in ("PASSIVE", "RESTART", "FULL", "TRUNCATE"):
        mode = "PASSIVE"
    c = connect()
    with _LOCK:
        row = c.execute(f"PRAGMA wal_checkpoint({mode})").fetchone()
    if not row:
        return (0, 0, 0)
    return (int(row[0]), int(row[1]), int(row[2]))


def wal_file_bytes() -> int:
    """On-disk size of the SQLite ``-wal`` sidecar (0 if absent)."""
    p = db_path().with_name(db_path().name + "-wal")
    try:
        return p.stat().st_size if p.exists() else 0
    except OSError:
        return 0


# Live chart max is 1000 bars; strategy lookback is ~200. Keep a cushion so
# dual-MA / ATR and the signals chart stay cache-hot without unbounded growth.
CANDLE_KEEP_BARS = 1200
# Worker snapshots ~1/min; keep ~7 days of equity history for the dashboard sparkline.
LEDGER_KEEP_ROWS = 10_080


def prune_candles(keep_bars: int = CANDLE_KEEP_BARS, conn=None) -> int:
    """Delete oldest candles beyond ``keep_bars`` per (venue, market, symbol, interval).

    Returns the number of rows deleted. No-op when keep_bars < 1.
    """
    if keep_bars < 1:
        return 0
    c = conn or connect()
    deleted = 0
    with _LOCK:
        series = c.execute(
            "SELECT venue, market, symbol, interval, COUNT(*) n FROM candles "
            "GROUP BY venue, market, symbol, interval HAVING n > ?",
            (keep_bars,),
        ).fetchall()
        for row in series:
            venue, market, symbol, interval, n = row[0], row[1], row[2], row[3], int(row[4])
            drop = n - keep_bars
            if drop <= 0:
                continue
            cur = c.execute(
                "DELETE FROM candles WHERE rowid IN ("
                "  SELECT rowid FROM candles WHERE venue=? AND market=? AND symbol=? AND interval=? "
                "  ORDER BY open_time ASC LIMIT ?"
                ")",
                (venue, market, symbol, interval, drop),
            )
            deleted += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    return deleted


def prune_ledger(keep_rows: int = LEDGER_KEEP_ROWS, conn=None) -> int:
    """Keep the newest ``keep_rows`` paper_ledger snapshots; delete older quiet history."""
    if keep_rows < 1:
        return 0
    c = conn or connect()
    with _LOCK:
        total = c.execute("SELECT COUNT(*) FROM paper_ledger").fetchone()[0]
        drop = int(total) - keep_rows
        if drop <= 0:
            return 0
        cur = c.execute(
            "DELETE FROM paper_ledger WHERE id IN ("
            "  SELECT id FROM paper_ledger ORDER BY id ASC LIMIT ?"
            ")",
            (drop,),
        )
        return int(cur.rowcount or 0)


def maintain_storage(*, truncate_wal: bool = False, prune: bool = False) -> dict:
    """Periodic 24/7 housekeeping: optional candle/ledger prune + WAL checkpoint.

    Always runs PASSIVE first (non-blocking). When ``truncate_wal`` is set, also
    tries TRUNCATE so the on-disk ``-wal`` file shrinks after heavy writes.
    """
    out: dict = {"passive": checkpoint_wal("PASSIVE"), "candles_deleted": 0, "ledger_deleted": 0,
                 "truncate": None, "wal_bytes": wal_file_bytes()}
    if prune:
        out["candles_deleted"] = prune_candles()
        out["ledger_deleted"] = prune_ledger()
        # Re-checkpoint after deletes so freed pages leave the WAL.
        out["passive"] = checkpoint_wal("PASSIVE")
    if truncate_wal:
        out["truncate"] = checkpoint_wal("TRUNCATE")
        out["wal_bytes"] = wal_file_bytes()
    return out

