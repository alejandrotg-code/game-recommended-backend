import pytest
from unittest.mock import AsyncMock, patch

def test_rag_recommend_success(client):
    """
    Verifica que el endpoint POST /api/rag/recommend responda con éxito
    cuando se envía una consulta válida en español.
    """
    mock_response = {
        "query_es": "Un juego relajante para pasar un día duro",
        "query_en": "A relaxing game to pass a hard day",
        "summary": "Aquí tienes excelentes opciones de granja y relajación.",
        "games": [
            {
                "app_id": 413150,
                "name": "Stardew Valley",
                "price": "13.99",
                "header_image": "https://cdn.akamai.steamstatic.com/steam/apps/413150/header.jpg",
                "genres": "Farming, Simulation, RPG",
                "tags": "Relaxing, Cozy, Crafting",
                "reason_ai": "Stardew Valley es perfecto para desconectar después de un día duro."
            }
        ]
    }

    with patch("services.rag_service.recommend_games_rag", new_callable=AsyncMock) as mock_rag:
        mock_rag.return_value = mock_response

        payload = {
            "query": "Un juego relajante para pasar un día duro",
            "top_k": 4
        }
        response = client.post("/api/rag/recommend", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["query_es"] == payload["query"]
        assert len(data["games"]) == 1
        assert data["games"][0]["name"] == "Stardew Valley"


def test_rag_recommend_empty_query(client):
    """
    Verifica que si se envía una consulta vacía o de solo espacios,
    el servidor responda con un error 400.
    """
    payload = {
        "query": "   ",
        "top_k": 4
    }
    response = client.post("/api/rag/recommend", json=payload)
    assert response.status_code == 400
    assert "no puede estar vacía" in response.json()["detail"]


def test_rag_recommend_top_k_20(client):
    """
    Verifica que se puedan solicitar 20 recomendaciones (top_k=20).
    """
    mock_response = {
        "query_es": "Juegos de estrategia",
        "query_en": "Strategy games",
        "summary": "Aquí tienes 20 juegos de estrategia.",
        "games": [{"app_id": i, "name": f"Strategy Game {i}"} for i in range(1, 21)]
    }

    with patch("services.rag_service.recommend_games_rag", new_callable=AsyncMock) as mock_rag:
        mock_rag.return_value = mock_response

        payload = {
            "query": "Juegos de estrategia",
            "top_k": 20
        }
        response = client.post("/api/rag/recommend", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 20
        mock_rag.assert_called_once_with(query_es="Juegos de estrategia", top_k=20)


def test_rag_recommend_invalid_top_k(client):
    """
    Verifica que top_k mayor a 20 devuelva un error de validación 422.
    """
    payload = {
        "query": "Juegos de simulación",
        "top_k": 25
    }
    response = client.post("/api/rag/recommend", json=payload)
    assert response.status_code == 422

