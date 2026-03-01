from __future__ import annotations
import time
import secrets
from typing import Any, Dict, Optional

# Simple in-memory cache for last N reports (no DB). Suitable for small deployments.
# Items expire after TTL seconds.
TTL_SECONDS = 60 * 60 * 6  # 6 hours
MAX_ITEMS = 200

_store: Dict[str, Dict[str, Any]] = {}

def _now() -> float:
    return time.time()

def _cleanup() -> None:
    # Remove expired
    now = _now()
    expired = [k for k, v in _store.items() if (now - v.get("ts", now)) > TTL_SECONDS]
    for k in expired:
        _store.pop(k, None)
    # Cap size (remove oldest)
    if len(_store) > MAX_ITEMS:
        items = sorted(_store.items(), key=lambda kv: kv[1].get("ts", 0.0))
        for k, _ in items[: max(0, len(_store) - MAX_ITEMS)]:
            _store.pop(k, None)

def put(payload: Dict[str, Any]) -> str:
    _cleanup()
    rid = secrets.token_urlsafe(16)
    payload = dict(payload)
    payload["ts"] = _now()
    _store[rid] = payload
    return rid

def get(rid: str) -> Optional[Dict[str, Any]]:
    _cleanup()
    item = _store.get(rid)
    if not item:
        return None
    if (_now() - item.get("ts", _now())) > TTL_SECONDS:
        _store.pop(rid, None)
        return None
    return item
