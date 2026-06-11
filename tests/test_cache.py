import sys, os, time, importlib.util, types, pytest
from cachetools import TTLCache

# Cargamos services/cache.py directamente, sin ejecutar services/__init__.py
# Esto evita arrastrar la dependencia de sentiment_service (que necesita el modelo .joblib)
_cache_spec = importlib.util.spec_from_file_location(
    "services.cache",
    os.path.join(os.path.dirname(__file__), "..", "services", "cache.py")
)
_cache_mod = importlib.util.module_from_spec(_cache_spec)
sys.modules["services.cache"] = _cache_mod
_cache_spec.loader.exec_module(_cache_mod)

CacheService = _cache_mod.CacheService


@pytest.fixture
def cache():
    """Instancia de CacheService aislada con TTL de 1s para tests rápidos."""
    _cache_mod._search_cache = TTLCache(maxsize=10, ttl=1)
    _cache_mod._analyze_cache = TTLCache(maxsize=10, ttl=1)
    return CacheService()


def test_search_miss_devuelve_none(cache):
    assert cache.get_search("hollow knight") is None


def test_search_hit_devuelve_datos(cache):
    datos = {"query": "hollow knight", "games": []}
    cache.set_search("hollow knight", datos)
    assert cache.get_search("hollow knight") == datos


def test_search_es_case_insensitive(cache):
    datos = {"query": "Portal", "games": []}
    cache.set_search("Portal", datos)
    assert cache.get_search("portal") == datos
    assert cache.get_search("PORTAL") == datos


def test_search_expira_tras_ttl(cache):
    cache.set_search("elden ring", {"games": []})
    time.sleep(1.1)
    assert cache.get_search("elden ring") is None


def test_analyze_miss_devuelve_none(cache):
    assert cache.get_analyze(400, 30) is None


def test_analyze_hit_devuelve_datos(cache):
    datos = {"app_id": 400, "recommendation_level": "Recomendado"}
    cache.set_analyze(400, 30, datos)
    assert cache.get_analyze(400, 30) == datos


def test_analyze_expira_tras_ttl(cache):
    cache.set_analyze(730, 30, {"app_id": 730})
    time.sleep(1.1)
    assert cache.get_analyze(730, 30) is None


def test_stats_refleja_tamanio_actual(cache):
    cache.set_search("celeste", {})
    cache.set_analyze(504230, 30, {})
    stats = cache.stats
    assert stats["search"]["size"] == 1
    assert stats["analyze"]["size"] == 1
    assert stats["search"]["maxsize"] == 10
    assert stats["analyze"]["ttl_seconds"] == 1