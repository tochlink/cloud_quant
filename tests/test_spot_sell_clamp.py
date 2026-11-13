"""现货平多卖出数量夹到交易所可用余额（买入手续费从到手币里扣）。"""
from qtw import engine, lots
from qtw.live import gate as gate_live
from qtw.live import okx as okx_live

FAKE = {"api_key": "k", "secret": "s", "passphrase": "p"}


class _Tr:
    def __init__(self, avail=None, err=None):
        self.avail, self.err = avail, err

    def spot_available(self, base):
        assert base == "BTC"
        if self.err:
            raise RuntimeError(self.err)
        return self.avail


def _lot(monkeypatch, step=1e-5, min_qty=1e-5):
    monkeypatch.setattr(lots, "spec", lambda v, s, m: lots.Lot(v, s, m, step, min_qty))


def test_clamp_to_available_after_base_fee(monkeypatch):
    _lot(monkeypatch)
    q, note = engine.clamp_spot_sell(_Tr(0.0099900), "okx", "BTCUSDT", 0.01, 70000)
    assert q == 0.00999 and "手续费" in note


def test_no_clamp_when_enough_or_unknown(monkeypatch):
    _lot(monkeypatch)
    assert engine.clamp_spot_sell(_Tr(0.02), "okx", "BTCUSDT", 0.01, 70000) == (0.01, "")
    q, note = engine.clamp_spot_sell(_Tr(err="timeout"), "gate", "BTCUSDT", 0.01, 70000)
    assert q == 0.01 and "查询失败" in note
    assert engine.clamp_spot_sell(object(), "okx", "BTCUSDT", 0.01, 70000) == (0.01, "")


def test_below_min_returns_zero(monkeypatch):
    _lot(monkeypatch, step=1e-5, min_qty=1e-4)
    q, _ = engine.clamp_spot_sell(_Tr(0.00005), "okx", "BTCUSDT", 0.01, 70000)
    assert q == 0.0


def test_okx_and_gate_spot_available_parse(monkeypatch):
    seen = []

    def okx_send(req):
        seen.append(req["url"])
        return {"code": "0", "data": [{"details": [{"ccy": "USDT", "availBal": "5"}, {"ccy": "BTC", "availBal": "0.00999"}]}]}

    def gate_send(req):
        seen.append(req["url"])
        return [{"currency": "BTC", "available": "0.00999", "locked": "0"}]

    monkeypatch.setattr(okx_live, "_send", okx_send)
    monkeypatch.setattr(gate_live, "_send", gate_send)
    assert okx_live.OkxTrader(FAKE).spot_available("BTC") == 0.00999
    assert gate_live.GateTrader(FAKE).spot_available("BTC") == 0.00999
    assert seen[0].endswith("/api/v5/account/balance?ccy=BTC")
    assert seen[1].endswith("/spot/accounts?currency=BTC")


def test_okx_signature_covers_query():
    req = okx_live.build(FAKE, "GET", "/api/v5/account/balance?ccy=BTC", None, demo=True, ts="2026-11-13T00:00:00.000Z")
    assert req["headers"]["OK-ACCESS-SIGN"] == okx_live.sign("s", "2026-11-13T00:00:00.000Z", "GET", "/api/v5/account/balance?ccy=BTC", "")
