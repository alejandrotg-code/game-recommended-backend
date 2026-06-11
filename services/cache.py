from cachetools import TTLCache
import threading

# TTLCache(maxsize, ttl) — maxsize evita memory leaks si hay muchas claves distintas
# search_cache: claves = término de búsqueda, TTL 5 minutos
# analyze_cache: claves = app_id, TTL 30 minutos
_search_cache: TTLCache = TTLCache(maxsize=200, ttl=300)
_analyze_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)

# Lock para thread-safety (FastAPI puede procesar requests concurrentes)
_search_lock = threading.Lock()
_analyze_lock = threading.Lock()


class CacheService:
    # ── Search ──────────────────────────────────────────────────
    def get_search(self, term: str) -> dict | None:
        with _search_lock:
            return _search_cache.get(term.lower().strip())

    def set_search(self, term: str, data: dict) -> None:
        with _search_lock:
            _search_cache[term.lower().strip()] = data

    # ── Analyze ─────────────────────────────────────────────────
    def get_analyze(self, app_id: int, limit: int) -> dict | None:
        with _analyze_lock:
            return _analyze_cache.get((app_id, limit))

    def set_analyze(self, app_id: int, limit: int, data: dict) -> None:
        with _analyze_lock:
            _analyze_cache[(app_id, limit)] = data

    # ── Stats  ───────────────
    @property
    def stats(self) -> dict:
        with _search_lock, _analyze_lock:
            return {
                "search": {
                    "size": len(_search_cache),
                    "maxsize": _search_cache.maxsize,
                    "ttl_seconds": _search_cache.ttl,
                },
                "analyze": {
                    "size": len(_analyze_cache),
                    "maxsize": _analyze_cache.maxsize,
                    "ttl_seconds": _analyze_cache.ttl,
                },
            }


cache_service = CacheService()