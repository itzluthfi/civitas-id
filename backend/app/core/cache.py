import time
from typing import Any, Optional, Dict

class TTLCache:
    def __init__(self, default_ttl: int = 86400):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        item = self._cache.get(key)
        if not item:
            return None
        if time.time() > item["expires_at"]:
            del self._cache[key]
            return None
        return item["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._cache[key] = {
            "value": value,
            "expires_at": expiry
        }

    def clear(self) -> None:
        self._cache.clear()

cache = TTLCache()
