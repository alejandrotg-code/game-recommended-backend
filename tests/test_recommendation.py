import pytest
from fastapi.testclient import TestClient
from services.recommendation import recommendation_service

def test_clean_description():
    """
    Verifica que la limpieza de la descripción elimine HTML, caracteres no deseados
    y convierta el texto a minúsculas.
    """
    dirty_text = "<b>¡Juego Increíble!</b> de Acción, Aventura & Disparos en 2026."
    cleaned = recommendation_service.clean_description(dirty_text)
    assert cleaned == "juego increíble de acción aventura disparos en 2026"


def test_recommend_endpoint_success(client):
    """
    Verifica que el endpoint /api/recommend responda con éxito y devuelva los géneros predichos
    y la lista de juegos de Steam asociados.
    """
    response = client.get("/api/recommend?description=un juego de guerra en primera persona de disparos")
    assert response.status_code == 200
    data = response.json()
    
    assert "cleaned_description" in data
    assert "predictions" in data
    assert data["top_genre"] == "Acción"
    assert data["top_probability"] == 90.0
    assert len(data["steam_games"]) > 0
    assert data["steam_games"][0]["name"] == "Counter-Strike"

def test_recommend_endpoint_missing_or_short_param(client):
    """
    Verifica que si falta el parámetro description o es demasiado corto, se devuelva un error 422.
    """
    # Sin parámetro
    response = client.get("/api/recommend")
    assert response.status_code == 422
    
    # Parámetro muy corto (mínimo 3 caracteres)
    response = client.get("/api/recommend?description=ab")
    assert response.status_code == 422

def test_recommend_endpoint_not_ready(client):
    """
    Verifica que si el servicio de recomendación no está listo (por ejemplo, fallo en la carga del modelo),
    el endpoint responda con un código de estado 503.
    """
    # Forzar temporalmente que no esté listo
    orig_model = recommendation_service.model
    recommendation_service.model = None
    
    try:
        response = client.get("/api/recommend?description=juego de naves")
        assert response.status_code == 503
        assert "no está cargado" in response.json()["detail"]
    finally:
        recommendation_service.model = orig_model
