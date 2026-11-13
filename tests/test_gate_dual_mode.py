"""Gate 双向持仓模式：调杠杆走 dual_comp 接口，下单参数不变；单向模式不变。"""
import qtw.live.guard as guard
from qtw.live import gate as gate_live

FAKE = {"api_key": "k", "secret": "s"}
SPEC = {"ct_val": 0.0001}


def _run(monkeypatch, dual):
    sent = []

    def fake_send(req):
        sent.append((req["method"], req["url"], req["body"]))
        if req["url"].endswith("/futures/usdt/accounts"):
            return {"total": "1", "in_dual_mode": dual}
        return {}

    monkeypatch.setattr(gate_live, "_send", fake_send)
    monkeypatch.setattr(guard, "require", lambda cfg, ex: None)
    t = gate_live.GateTrader(FAKE, testnet=False)
    t.place_order({}, "BTCUSDT", "perp", "open_short", 0.002, 69000, SPEC)
    t.place_order({}, "BTCUSDT", "perp", "open_short", 0.002, 69000, SPEC)
    t.place_order({}, "BTCUSDT", "perp", "close_short", 0.002, 69000, SPEC)
    return sent


def test_dual_mode_uses_dual_comp_leverage(monkeypatch):
    sent = _run(monkeypatch, True)
    assert sum(u.endswith("/futures/usdt/accounts") for _, u, _ in sent) == 1
    lev = [u for _, u, _ in sent if "leverage" in u]
    assert lev and all("/dual_comp/positions/BTC_USDT/leverage?leverage=1" in u for u in lev)
    orders = [b for _, u, b in sent if u.endswith("/futures/usdt/orders")]
    assert '"size":-20' in orders[0] and '"size":20' in orders[2] and '"reduce_only":true' in orders[2]


def test_single_mode_unchanged(monkeypatch):
    sent = _run(monkeypatch, False)
    lev = [u for _, u, _ in sent if "leverage" in u]
    assert lev and all("/futures/usdt/positions/BTC_USDT/leverage?leverage=1" in u and "dual_comp" not in u for u in lev)
