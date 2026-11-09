"""日志脱敏：任何已加载的密钥 / 口令在日志中都会被替换成 ***。"""
from __future__ import annotations

import logging
import threading

_SECRETS: set[str] = set()
_LOCK = threading.Lock()


def register_secret(value: str | None) -> None:
    if value and len(value) >= 4:
        with _LOCK:
            _SECRETS.add(value)


def redact(text: str) -> str:
    with _LOCK:
        items = sorted(_SECRETS, key=len, reverse=True)
    for s in items:
        if s in text:
            text = text.replace(s, "***")
    return text


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        try:
            msg = record.getMessage()
        except Exception:
            return True
        red = redact(msg)
        if red != msg:
            record.msg, record.args = red, ()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not any(isinstance(f, RedactFilter) for h in root.handlers for f in h.filters):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler.addFilter(RedactFilter())
        root.handlers = [handler]
    root.setLevel(level)
