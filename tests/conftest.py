import os
import tempfile

# 测试中：无条件禁止实盘，数据目录用临时目录
os.environ["QTW_FORBID_LIVE"] = "1"
os.environ.pop("QTW_ALLOW_LIVE_ORDERS", None)
_tmp = tempfile.mkdtemp(prefix="qtw-test-")
os.environ["QTW_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["QTW_OUTPUT_DIR"] = os.path.join(_tmp, "output")

import pytest


@pytest.fixture(autouse=True)
def _offline_lot_spec(monkeypatch, request):
    """单元测试不访问交易所元数据接口：默认用 1e-8 步长（等同不取整）。需要真实取整逻辑的测试自己构造 Lot。"""
    if request.node.get_closest_marker("real_lots"):
        return
    from qtw import lots
    monkeypatch.setattr(lots, "spec", lambda venue, symbol, market: lots.Lot(venue, symbol, market, 1e-8, 0.0,
                                                                              1.0, 1e-8 if market == "perp" else 0.0))


def pytest_configure(config):
    config.addinivalue_line("markers", "real_lots: 使用测试自己构造的 Lot，不打补丁")
