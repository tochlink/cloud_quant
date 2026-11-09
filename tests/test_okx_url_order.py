"""OKX public WS: prefer :443 before :8443 (many networks reset 8443)."""
from qtw import stream


def test_okx_public_and_business_prefer_443_before_8443():
    for urls in (stream.OKX_PUBLIC, stream.OKX_BUSINESS):
        assert urls[0].startswith("wss://ws.okx.com/ws/")
        assert ":8443" not in urls[0]
        assert any(":8443" in u for u in urls), "8443 kept as fallback"
        assert any("wsaws.okx.com" in u for u in urls)
