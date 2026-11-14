"""全景页面（/panorama/）：静态挂载、ES 模块 MIME、导航入口和 three.js 许可证都在。"""
from fastapi.testclient import TestClient

from qtw.app import app
from qtw.paths import STATIC_DIR


def test_panorama_index_served_with_redirect():
    client = TestClient(app)
    r = client.get("/panorama", follow_redirects=False)
    assert r.status_code in (301, 307, 308)
    assert r.headers["location"].endswith("/panorama/")
    r = client.get("/panorama/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert 'id="pg-tabs"' in r.text and 'src="js/main.js"' in r.text


def test_panorama_modules_are_javascript():
    client = TestClient(app)
    for path in ("/panorama/js/main.js", "/panorama/js/gate.js", "/panorama/vendor/three.module.min.js"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "javascript" in r.headers["content-type"], (path, r.headers["content-type"])
    assert client.get("/panorama/css/app.css").status_code == 200
    assert client.get("/panorama/vendor/three.LICENSE").status_code == 200


def test_panorama_nav_entry_and_no_secrets_or_ide_files():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert '["panorama", "panorama", "全景"' in js
    root = STATIC_DIR / "panorama"
    names = {p.name for p in root.rglob("*")}
    assert ".idea" not in names and ".git" not in names
    assert "MIT" in (root / "vendor" / "three.LICENSE").read_text(encoding="utf-8")
