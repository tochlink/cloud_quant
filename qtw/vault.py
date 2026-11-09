"""API 密钥加密存储。

* 密文：data/secrets.enc（Fernet = AES-128-CBC + HMAC-SHA256）
* 主密钥两种来源（二选一）：
  1. 环境变量 QTW_MASTER_PASSPHRASE：用 scrypt(口令, data/vault.salt) 派生，磁盘上不存主密钥；
  2. 否则使用本地密钥文件 data/vault.key（首次自动生成，权限 0600）。
* data/ 整个目录在 .gitignore 中；密钥永远不写入 CSV / 日志，前端只拿到掩码。
"""
from __future__ import annotations

import base64
import json
import os
import threading

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .logsafe import register_secret
from .paths import DATA_DIR, ensure_dirs

FIELDS = {"okx": ["api_key", "secret", "passphrase"], "gate": ["api_key", "secret"]}
_LOCK = threading.Lock()


def _paths():
    return DATA_DIR / "secrets.enc", DATA_DIR / "vault.key", DATA_DIR / "vault.salt"


def _write_private(path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(path, 0o600)


def key_source() -> str:
    return "passphrase" if os.environ.get("QTW_MASTER_PASSPHRASE") else "keyfile"


def _fernet() -> Fernet:
    ensure_dirs()
    _, keyf, saltf = _paths()
    pw = os.environ.get("QTW_MASTER_PASSPHRASE")
    if pw:
        if not saltf.exists():
            _write_private(saltf, os.urandom(16))
        kdf = Scrypt(salt=saltf.read_bytes(), length=32, n=2**15, r=8, p=1)
        return Fernet(base64.urlsafe_b64encode(kdf.derive(pw.encode())))
    if not keyf.exists():
        _write_private(keyf, Fernet.generate_key())
    return Fernet(keyf.read_bytes().strip())


def _load_all() -> dict:
    enc, _, _ = _paths()
    if not enc.exists():
        return {}
    try:
        data = json.loads(_fernet().decrypt(enc.read_bytes()))
    except InvalidToken as e:
        raise RuntimeError("无法解密 secrets.enc：主口令或 vault.key 不匹配") from e
    for ex in data.values():
        for v in ex.values():
            register_secret(v)
    return data


def _save_all(data: dict) -> None:
    enc, _, _ = _paths()
    _write_private(enc, _fernet().encrypt(json.dumps(data).encode()))


def set_keys(exchange: str, values: dict) -> None:
    if exchange not in FIELDS:
        raise ValueError("exchange 必须是 okx 或 gate")
    with _LOCK:
        data = _load_all()
        cur = data.get(exchange, {})
        for f in FIELDS[exchange]:
            v = (values.get(f) or "").strip()
            if v:  # 空字段 = 保持原值
                cur[f] = v
                register_secret(v)
        data[exchange] = cur
        _save_all(data)


def delete_keys(exchange: str) -> None:
    with _LOCK:
        data = _load_all()
        data.pop(exchange, None)
        _save_all(data)


def get_keys(exchange: str) -> dict | None:
    """仅供后端签名使用；绝不返回给前端。"""
    with _LOCK:
        k = _load_all().get(exchange)
    if not k or not all(k.get(f) for f in FIELDS[exchange]):
        return None
    return k


def mask(v: str | None) -> str:
    if not v:
        return ""
    if len(v) <= 8:
        return "•" * len(v)
    return f"{v[:4]}••••••{v[-4:]}"


def status() -> dict:
    with _LOCK:
        try:
            data = _load_all()
            err = ""
        except RuntimeError as e:
            data, err = {}, str(e)
    out = {"key_source": key_source(), "error": err}
    for ex, fields in FIELDS.items():
        k = data.get(ex, {})
        out[ex] = {
            "configured": all(k.get(f) for f in fields),
            "api_key_masked": mask(k.get("api_key")),
            **{f"{f}_set": bool(k.get(f)) for f in fields if f != "api_key"},
        }
    return out
