from unittest.mock import patch, PropertyMock


def test_health_modelo_cargado(client):
    """Con modelo cargado debe retornar status 'healthy'."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["model"]["loaded"] is True
    assert "uptime" in data
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_health_estructura_cache(client):
    """El campo cache debe exponer stats de search y analyze."""
    response = client.get("/api/health")
    data = response.json()

    cache = data["cache"]
    assert "search" in cache
    assert "analyze" in cache

    for section in ("search", "analyze"):
        assert "size" in cache[section]
        assert "maxsize" in cache[section]
        assert "ttl_seconds" in cache[section]


def test_health_modelo_degradado(client):
    """Sin modelo cargado debe retornar status 'degraded'."""
    import services.sentiment as _sent_mod
    # Parcheamos model_loaded en la clase concreta del singleton (que es el MockSentimentService)
    _cls = type(_sent_mod.sentiment_service)
    original_prop = _cls.__dict__.get("model_loaded", True)
    _cls.model_loaded = False
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["model"]["loaded"] is False
    finally:
        _cls.model_loaded = True


def test_health_uptime_formato(client):
    """El campo uptime debe ser un string legible que termina en 's'."""
    response = client.get("/api/health")
    data = response.json()
    assert isinstance(data["uptime"], str)
    assert data["uptime"].endswith("s")