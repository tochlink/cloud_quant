"""OKX 开平仓模式（long_short_mode）下永续单带 posSide=short、不带 reduceOnly；买卖模式不变。"""
from qtw.live import okx as okx_live

FAKE = {"api_key": "k", "secret": "s", "passphrase": "p"}
SPEC = {"ct_val": 0.01, "lot_sz": 0.01}


def test_net_mode_unchanged():
    p = okx_live.order_payload("BTCUSDT", "perp", "close_short", 0.002, 69000, SPEC)
    assert p["reduceOnly"] is True and "posSide" not in p
    p = okx_live.order_payload("BTCUSDT", "perp", "open_short", 0.002, 69000, SPEC)
    assert "posSide" not in p and "reduceOnly" not in p


def test_long_short_mode_adds_pos_side():
    for a in ("open_short", "close_short"):
        p = okx_live.order_payload("BTCUSDT", "perp", a, 0.002, 69000, SPEC, "long_short_mode")
        assert p["posSide"] == "short" and "reduceOnly" not in p
    s = okx_live.order_payload("BTCUSDT", "spot", "close_long", 0.002, 69000, None, "long_short_mode")
    assert "posSide" not in s


def test_place_order_reads_pos_mode_once(monkeypatch):
    sent = []

    def fake_send(req):
        sent.append((req["url"], req["body"]))
        if req["url"].endswith("/api/v5/account/config"):
            return {"code": "0", "data": [{"posMode": "long_short_mode"}]}
        return {"code": "0", "data": [{}]}

    monkeypatch.setattr(okx_live, "_send", fake_send)
    import qtw.live.guard as guard
    monkeypatch.setattr(guard, "require", lambda cfg, ex: None)
    t = okx_live.OkxTrader(FAKE)
    t.place_order({}, "BTCUSDT", "perp", "open_short", 0.002, 69000, SPEC)
    t.place_order({}, "BTCUSDT", "perp", "close_short", 0.002, 69000, SPEC)
    assert sum(u.endswith("/account/config") for u, _ in sent) == 1
    lev = next(b for u, b in sent if u.endswith("/set-leverage"))
    assert '"posSide":"short"' in lev
    orders = [b for u, b in sent if u.endswith("/trade/order")]
    assert all('"posSide":"short"' in b and "reduceOnly" not in b for b in orders)
