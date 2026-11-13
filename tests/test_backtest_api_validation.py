"""/api/backtest 参数错误应返回 400 + 中文原因（校验在拉行情之前，不触网）。"""
import pytest
from fastapi.testclient import TestClient

from qtw.app import app


@pytest.mark.parametrize("body", [{"fast_ma": 200, "slow_ma": 50}, {"bars": "abc"}, {"atr_stop_mult": "x"}, {"confirm_bars": 9}])
def test_backtest_bad_params_400(body):
    r = TestClient(app, raise_server_exceptions=False).post("/api/backtest", json=body)
    assert r.status_code == 400, r.text
