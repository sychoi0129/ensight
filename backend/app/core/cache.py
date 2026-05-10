"""간단한 인메모리 TTL 캐시.

DB(미국 동부 Neon)까지의 왕복 비용이 커서 동일 파라미터로 반복 호출되는
조회 API 응답을 잠깐 캐시한다. 단일 프로세스(uvicorn 1 worker) 기준.
멀티 워커 또는 다중 인스턴스 환경에선 Redis 등 외부 캐시로 대체 권장.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable

_DEFAULT_MAX_ITEMS = 256


class _TTLCache:
    def __init__(self, max_items: int = _DEFAULT_MAX_ITEMS) -> None:
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_items = max_items
        self._lock = asyncio.Lock()

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._max_items:
            self._store.popitem(last=False)

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        async with self._lock:
            self._store[key] = (time.monotonic() + ttl_seconds, value)
            self._store.move_to_end(key)
            self._evict_if_needed()


_cache = _TTLCache()


def _build_key(prefix: str, args: tuple, kwargs: dict) -> str:
    try:
        payload = json.dumps([args, kwargs], default=str, sort_keys=True)
    except TypeError:
        payload = repr((args, kwargs))
    return f"{prefix}::{payload}"


def cache_response(ttl_seconds: float, key_prefix: str | None = None) -> Callable:
    """동기/비동기 함수의 결과를 (인자 기반) 키로 잠깐 캐시한다."""

    def decorator(fn: Callable) -> Callable:
        prefix = key_prefix or f"{fn.__module__}.{fn.__qualname__}"
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = _build_key(prefix, args, kwargs)
                hit = await _cache.get(key)
                if hit is not None:
                    return hit
                result = await fn(*args, **kwargs)
                await _cache.set(key, result, ttl_seconds)
                return result

            return async_wrapper

        @wraps(fn)
        async def sync_wrapper(*args, **kwargs):
            key = _build_key(prefix, args, kwargs)
            hit = await _cache.get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            await _cache.set(key, result, ttl_seconds)
            return result

        return sync_wrapper

    return decorator
