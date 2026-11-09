import json
import os

import pytest

from qtw import settings as S
from qtw import vault
from qtw.live import guard
from qtw.live import okx as okx_live
from qtw.live import gate as gate_live
from qtw.logsafe import redact


FAKE = {"api_key": "TESTKEY-1234567890-abcd", "secret": "TESTSECRET-zzzz-9999", "passphrase": "TESTPASS-777"}


def test_vault_encrypts_and_masks(tmp_path):
    vault.set_keys("okx", FAKE)
    raw = (vault._paths()[0]).read_bytes()
    for v in FAKE.values():
        assert v.encode() not in raw
    st = json.dumps(vault.status())
    for v in FAKE.values():
        assert v not in st
    assert vault.status()["okx"]["configured"]
    assert vault.get_keys("okx")["secret"] == FAKE["secret"]
    assert os.stat(vault._paths()[1]).st_mode & 0o077 == 0
    assert "***" in redact(f"oops {FAKE['secret']}")


def test_live_guard_blocks_by_default():
    cfg = S.load()
    ok, reasons = guard.check(cfg, "okx")
    assert not ok and reasons
    cfg["live"].update(mode="live", live_enabled=True, confirm_phrase=S.LIVE_CONFIRM_PHRASE)
    ok, _ = guard.check(cfg, "okx")
    assert not ok  # QTW_FORBID_LIVE=1 + 未设置 QTW_ALLOW_LIVE_ORDERS


def test_place_order_never_sends_when_blocked(monkeypatch):
    called = []
    monkeypatch.setattr(okx_live, "_send", lambda req: called.append(req))
    monkeypatch.setattr(gate_live, "_send", lambda req: called.append(req))
    cfg = S.load()
    with pytest.raises(guard.LiveBlocked):
        okx_live.OkxTrader(FAKE).place_order(cfg, "BTCUSDT", "spot", "open_long", 0.001, 70000)
    with pytest.raises(guard.LiveBlocked):
        gate_live.GateTrader(FAKE).place_order(cfg, "BTCUSDT", "perp", "open_short", 0.001, 70000, {"ct_val": 0.0001})
    assert called == []


def test_signatures_and_preview_redacted():
    sig = okx_live.sign("secret", "2020-12-08T09:08:57.715Z", "GET", "/api/v5/account/balance?ccy=BTC", "")
    assert isinstance(sig, str) and len(sig) == 44
    prev = okx_live.OkxTrader(FAKE).preview_order("ETHUSDT", "perp", "open_short", 1.234, 2000, {"ct_val": 0.1, "lot_sz": 0.01})
    s = json.dumps(prev)
    assert FAKE["api_key"] not in s and FAKE["passphrase"] not in s
    assert prev["headers"]["x-simulated-trading"] == "1"
    assert json.loads(prev["body"])["sz"] == "12.34"
    g = gate_live.GateTrader(FAKE).preview_order("ETHUSDT", "perp", "open_short", 1.234, 2000, {"ct_val": 0.01})
    assert json.loads(g["body"])["size"] == -123 and FAKE["api_key"] not in json.dumps(g)
    assert len(gate_live.sign("s", "POST", "/spot/orders", "", "{}", "1")) == 128
