"""OKX public WS/REST: official 443 hosts only by default (no retired aws / :8443)."""
from qtw import stream
from qtw.market import okx as okx_mod
from qtw.net import okx_rest_bases, okx_ws_urls


def test_okx_public_and_business_use_official_443():
    for urls in (stream.OKX_PUBLIC, stream.OKX_BUSINESS, okx_ws_urls("public"), okx_ws_urls("business")):
        assert urls[0].startswith("wss://ws.okx.com/ws/")
        assert ":8443" not in urls[0]
        assert all("wsaws.okx.com" not in u for u in urls)
        assert all(":8443" not in u for u in urls)


def test_okx_rest_defaults_are_official_openapi_then_www():
    assert okx_mod.BASES[0] == "https://openapi.okx.com"
    assert "https://www.okx.com" in okx_mod.BASES
    assert all("aws.okx.com" not in b for b in okx_mod.BASES)
    bases = okx_rest_bases()
    assert bases[0] == "https://openapi.okx.com"
    assert "https://www.okx.com" in bases


def test_okx_ws_host_env_overrides_allowed_official(monkeypatch):
    monkeypatch.setenv("QTW_OKX_WS_HOST", "wsus.okx.com")
    assert okx_ws_urls("public") == ["wss://wsus.okx.com/ws/v5/public"]
    assert okx_ws_urls("business") == ["wss://wsus.okx.com/ws/v5/business"]


def test_okx_rest_host_env_prepends_allowed_official(monkeypatch):
    monkeypatch.setenv("QTW_OKX_REST_HOST", "www.okx.com")
    bases = okx_rest_bases()
    assert bases[0] == "https://www.okx.com"
    assert bases[1] == "https://openapi.okx.com"


def test_okx_host_env_rejects_unknown_or_retired(monkeypatch):
    monkeypatch.setenv("QTW_OKX_WS_HOST", "wsaws.okx.com")
    assert okx_ws_urls("public") == ["wss://ws.okx.com/ws/v5/public"]
    monkeypatch.setenv("QTW_OKX_REST_HOST", "aws.okx.com")
    assert okx_rest_bases()[0] == "https://openapi.okx.com"
    monkeypatch.setenv("QTW_OKX_WS_HOST", "evil.example.com")
    assert okx_ws_urls("business") == ["wss://ws.okx.com/ws/v5/business"]
