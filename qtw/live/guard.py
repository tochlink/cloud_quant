"""实盘三重闸门。任何一个不满足都只会生成“预演订单”（dry-run），不会发出 HTTP 请求。

1. settings.live.mode == "live" 且 live_enabled == true
2. settings.live.confirm_phrase == LIVE_CONFIRM_PHRASE（页面上手动输入确认语）
3. 进程环境变量 QTW_ALLOW_LIVE_ORDERS == "1"（启动时显式开启）
另外：已存入对应交易所的完整 API 密钥；QTW_FORBID_LIVE=1（测试用）时无条件禁止。
"""
from __future__ import annotations

import os

from qtw import settings as S
from qtw import vault


class LiveBlocked(RuntimeError):
    pass


def check(cfg: dict, exchange: str) -> tuple[bool, list[str]]:
    reasons = []
    if os.environ.get("QTW_FORBID_LIVE") == "1":
        reasons.append("QTW_FORBID_LIVE=1（测试/安全模式）")
    lv = cfg["live"]
    if lv["mode"] != "live":
        reasons.append("当前为纸面模式")
    if not S._as_bool(lv["live_enabled"]):  # 字符串 "false" 视为关闭
        reasons.append("实盘开关未打开")
    if lv.get("confirm_phrase") != S.LIVE_CONFIRM_PHRASE:
        reasons.append("未输入实盘风险确认语")
    if os.environ.get("QTW_ALLOW_LIVE_ORDERS") != "1":
        reasons.append("启动时未设置 QTW_ALLOW_LIVE_ORDERS=1")
    if not vault.get_keys(exchange):
        reasons.append(f"{exchange.upper()} API 密钥未完整配置")
    return (not reasons), reasons


def require(cfg: dict, exchange: str) -> None:
    ok, reasons = check(cfg, exchange)
    if not ok:
        raise LiveBlocked("；".join(reasons))
