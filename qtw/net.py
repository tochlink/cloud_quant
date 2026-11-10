"""行情网络辅助：代理、官方 OKX 域名、重连退避与错误归类。

官方 Global 域名（OKX 文档 changelog：2025-04-28 / 2026-05-20 / 2026-10-31）：
  REST: https://openapi.okx.com（推荐）、https://www.okx.com（仍可用，未废弃）
  WS:   wss://ws.okx.com/ws/v5/public 与 .../business（443 端口；wss 默认即 443）

地区站（仅当账户注册在对应站点时使用，通过环境变量指定，不作默认）：
  REST: us.okx.com、eea.okx.com、tr.okx.com
  WS:   wsus.okx.com、wseea.okx.com

已停用、默认不再连接：
  aws.okx.com / wsaws.okx.com — 2025-04-28 停止服务
  WebSocket :8443 — 公网已于 2026-10-31 停止（此前 443 已可用）
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlparse, urlunparse

log = logging.getLogger("qtw.net")

OKX_REST_DEFAULTS = ["https://openapi.okx.com", "https://www.okx.com"]
OKX_WS_DEFAULT_HOST = "ws.okx.com"

ALLOWED_OKX_REST_HOSTS = frozenset({
    "openapi.okx.com", "www.okx.com", "us.okx.com", "eea.okx.com", "tr.okx.com",
})
ALLOWED_OKX_WS_HOSTS = frozenset({
    "ws.okx.com", "wsus.okx.com", "wseea.okx.com",
})

RECONNECT_BACKOFF_START_SEC = 5.0
RECONNECT_BACKOFF_CAP_SEC = 300.0
RECONNECT_LOG_FIRST = 3
RECONNECT_LOG_EVERY = 10
RECONNECT_LOG_INTERVAL_SEC = 600.0

_PROXY_STD_KEYS = (
    "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy",
)
_OFF_VALUES = frozenset({"", "none", "off", "direct", "0"})


def env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def resolve_proxy() -> str | None:
    """Explicit proxy URL, or None to go direct (no OS/env autodetect in websockets).

    Priority: QTW_PROXY, then HTTPS_PROXY / HTTP_PROXY / ALL_PROXY (and lowercase).
    QTW_PROXY=none (or off/direct/0) forces a direct connection even if other
    proxy env vars are set.
    """
    if "QTW_PROXY" in os.environ:
        val = (os.environ.get("QTW_PROXY") or "").strip()
        if val.lower() in _OFF_VALUES:
            return None
        return val
    for key in _PROXY_STD_KEYS:
        val = (os.environ.get(key) or "").strip()
        if val and val.lower() not in _OFF_VALUES:
            return val
    return None


def redact_proxy(url: str) -> str:
    """Strip userinfo from a proxy URL for logs."""
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if p.port:
            host = f"{host}:{p.port}"
        if p.username:
            host = f"***@{host}"
        return urlunparse((p.scheme, host, p.path or "", "", "", ""))
    except Exception:  # noqa: BLE001
        return "(proxy)"


def apply_proxy_to_session(session) -> str | None:
    """Apply resolve_proxy() to a requests.Session. Returns the proxy or None.

    QTW_PROXY=none also disables requests' default env-proxy lookup (trust_env).
    """
    if "QTW_PROXY" in os.environ and (os.environ.get("QTW_PROXY") or "").strip().lower() in _OFF_VALUES:
        session.trust_env = False
        session.proxies.pop("http", None)
        session.proxies.pop("https", None)
        return None
    proxy = resolve_proxy()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    return proxy


def _parse_host_port(raw: str, *, scheme: str) -> tuple[str, int | None]:
    s = (raw or "").strip()
    if not s:
        return "", None
    if "://" not in s:
        s = f"{scheme}://{s}"
    p = urlparse(s)
    return (p.hostname or "").lower(), p.port


def okx_rest_bases() -> list[str]:
    """Official REST bases, with an optional allowed QTW_OKX_REST_HOST tried first."""
    bases = list(OKX_REST_DEFAULTS)
    raw = (os.environ.get("QTW_OKX_REST_HOST") or "").strip()
    if not raw:
        return bases
    host, _port = _parse_host_port(raw, scheme="https")
    if host in ALLOWED_OKX_REST_HOSTS:
        url = f"https://{host}"
        return [url] + [b for b in bases if b != url]
    log.warning(
        "忽略非法 QTW_OKX_REST_HOST=%s（只接受官方域名：%s）",
        raw, "、".join(sorted(ALLOWED_OKX_REST_HOSTS)),
    )
    return bases


def okx_ws_urls(channel: str) -> list[str]:
    """Official OKX public/business WebSocket URLs (port 443 unless the env sets a port)."""
    if channel not in ("public", "business"):
        raise ValueError(f"OKX WS 通道只能是 public 或 business，收到 {channel!r}")
    host, port = OKX_WS_DEFAULT_HOST, None
    raw = (os.environ.get("QTW_OKX_WS_HOST") or "").strip()
    if raw:
        h, p = _parse_host_port(raw, scheme="wss")
        if h in ALLOWED_OKX_WS_HOSTS:
            host, port = h, p
        else:
            log.warning(
                "忽略非法 QTW_OKX_WS_HOST=%s（只接受官方域名：%s）",
                raw, "、".join(sorted(ALLOWED_OKX_WS_HOSTS)),
            )
    if port:
        return [f"wss://{host}:{port}/ws/v5/{channel}"]
    return [f"wss://{host}/ws/v5/{channel}"]


def reconnect_backoff(fail_count: int) -> float:
    """Consecutive-failure backoff: 5s → 10 → 20 → … capped at 300s. fail_count is 1-based."""
    n = max(int(fail_count), 1)
    return min(RECONNECT_BACKOFF_START_SEC * (2 ** (n - 1)), RECONNECT_BACKOFF_CAP_SEC)


def classify_ws_error(exc: BaseException) -> tuple[str, str]:
    """Return (exception class name, short Chinese reason) for logs and UI hints."""
    name = type(exc).__name__
    text = f"{name} {exc}".lower()
    compact = text.replace(" ", "").replace("_", "")
    # Wrapped errors (ConnectionError from wait_for, OSError) still mention the cause.
    if (
        name == "gaierror"
        or "gaierror" in compact
        or "nameresolutionerror" in compact
        or "getaddrinfo" in compact
        or "name or service not known" in text
        or "temporary failure in name resolution" in text
        or "nodename nor servname" in text
        or "name resolution" in text
    ):
        return name, "DNS 解析失败"
    if name == "ConnectionResetError" or "connection reset" in text or "connectionreseterror" in compact:
        return name, "连接被重置"
    if name == "ConnectionRefusedError" or "connection refused" in text or "connectionrefusederror" in compact:
        return name, "连接被拒绝"
    if (
        name in ("TimeoutError", "CancelledError")
        or "timed out" in text
        or "timeout" in text
        or "timeouterror" in compact
        or "未能完成" in str(exc)
    ):
        return name, "连接超时"
    if "proxy" in text:
        return name, "代理连接失败"
    return name, name


def should_log_reconnect(fail_count: int, last_log_at: float, now: float) -> bool:
    """Log the first few failures, the first summary, then every 10th or every 10 minutes."""
    if fail_count <= RECONNECT_LOG_FIRST + 1:
        return True
    if fail_count % RECONNECT_LOG_EVERY == 0:
        return True
    if last_log_at and (now - last_log_at) >= RECONNECT_LOG_INTERVAL_SEC:
        return True
    return False


def reconnect_summary(name: str, fail_count: int, reason: str, backoff: float) -> str:
    venue = "OKX" if (name or "").startswith("okx") else "Gate" if (name or "").startswith("gate") else name
    if (name or "").startswith("okx"):
        return (
            f"{venue} 实时连接持续失败 {fail_count} 次（{reason}），"
            f"{backoff:.0f} 秒后重试；已改用 REST 轮询 / Gate 行情，不会编造价格。"
            f"如在国内请配置代理后再启动，例如 set HTTPS_PROXY=http://127.0.0.1:7890"
        )
    return (
        f"{venue} 实时连接持续失败 {fail_count} 次（{reason}），"
        f"{backoff:.0f} 秒后重试；已改用 REST 轮询，不会编造价格。"
        f"如需要请配置代理 HTTPS_PROXY 或 QTW_PROXY"
    )


def venue_unreachable_hint(
    *,
    venue: str,
    mode: str,
    quotes_ws_fresh: int,
    quotes_rest_fresh: int,
    rest_errors: dict,
    last_errors: list[str] | None = None,
    okx_ws_disabled: bool = False,
) -> str:
    """Short Chinese status hint for the UI; empty when nothing useful to say."""
    v = (venue or "").strip().lower()
    label = "OKX" if v == "okx" else "Gate" if v in ("gate", "gateio", "gate.io") else (venue or "").upper() or "行情"
    reasons = []
    for e in last_errors or []:
        if not e:
            continue
        _, zh = classify_ws_error(RuntimeError(e))
        # classify_ws_error on a bare string still inspects the text
        reasons.append(zh if zh != "RuntimeError" else e.split(":")[0][:40])
    for err in list((rest_errors or {}).values())[:4]:
        _, zh = classify_ws_error(RuntimeError(str(err)))
        reasons.append(zh if zh != "RuntimeError" else str(err)[:40])
    # Prefer specific labels when present
    why = ""
    for token in ("DNS 解析失败", "连接被重置", "连接被拒绝", "连接超时", "代理连接失败"):
        if token in reasons:
            why = token
            break
    if not why and reasons:
        why = reasons[0]

    if okx_ws_disabled and v == "okx":
        if quotes_rest_fresh > 0:
            return "已关闭 OKX WebSocket（QTW_DISABLE_OKX_WS=1），正在使用官方 REST 轮询；Gate 行情不受影响，不会编造价格。"
        if rest_errors or mode == "down":
            extra = f"（{why}）" if why else ""
            return (
                f"已关闭 OKX WebSocket，且 OKX REST 也不可达{extra}，不会编造价格。"
                f"可在设置中改用 Gate 行情，或配置代理后再试，例如 set HTTPS_PROXY=http://127.0.0.1:7890"
            )
        return "已关闭 OKX WebSocket（QTW_DISABLE_OKX_WS=1），OKX 价格走官方 REST 轮询。"

    if mode == "ws":
        return ""
    if quotes_rest_fresh > 0 and mode in ("rest", "recovering"):
        return (
            f"{label} WebSocket 暂不可用，已改用官方 REST 轮询，价格仍是真实报价。"
            f"如在国内请配置代理后再启动，例如 set HTTPS_PROXY=http://127.0.0.1:7890"
        )
    if quotes_ws_fresh == 0 and quotes_rest_fresh == 0 and mode in ("rest", "down", "recovering"):
        extra = f"（{why}）" if why else ""
        other = "可改用 Gate 行情，或" if v == "okx" else "可改用 OKX 行情，或"
        return (
            f"{label} 实时与 REST 均不可达{extra}，不会编造价格。"
            f"{other}配置代理后再试，例如 set HTTPS_PROXY=http://127.0.0.1:7890"
        )
    return ""
