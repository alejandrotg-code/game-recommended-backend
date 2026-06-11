from unittest.mock import patch

def test_read_root(client):
    """
    Verifica que el endpoint raíz '/' retorne el estado de la aplicación.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "model_loaded" in data

@patch("routers.games.buscar_juegos_steam")
def test_search_endpoint(mock_buscar, client):
    """
    Verifica que el endpoint '/api/search' responda correctamente llamando al servicio de Steam.
    """
    mock_buscar.return_value = {
        "query": "Portal",
        "total_found": 1,
        "games": [{"id": 400, "name": "Portal", "price": "9.75 EUR", "image": "img", "metascore": 95}]
    }
    
    response = client.get("/api/search?term=Portal")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Portal"
    assert len(data["games"]) == 1
    assert data["games"][0]["name"] == "Portal"

@patch("routers.games.obtener_detalles_juego")
@patch("routers.games.obtener_reseñas_steam")
def test_analyze_endpoint(mock_obtener_reseñas, mock_obtener_detalles, client):
    """
    Verifica que el endpoint '/api/analyze/{app_id}' clasifique correctamente
    las reseñas y calcule de forma correcta las estadísticas de recomendación.
    """
    mock_obtener_detalles.return_value = {
        "developer": "Valve",
        "genres": ["Action"],
        "release_date": "10 Oct 2007",
        "price": "9.75 EUR"
    }
    
    mock_obtener_reseñas.return_value = [
        {
            "recommendationid": "1",
            "author": {"personaname": "User1", "playtime_forever": 100},
            "review": "Es un buen juego",
            "voted_up": True
        },
        {
            "recommendationid": "2",
            "author": {"personaname": "User2", "playtime_forever": 200},
            "review": "Es un mal juego, aburrido",
            "voted_up": False
        }
    ]
    
    response = client.get("/api/analyze/400?limit=5")
    assert response.status_code == 200
    data = response.json()
    
    assert data["app_id"] == 400
    assert data["total_reviews_analyzed"] == 2
    assert data["recommendation_level"] == "Mixto"  # 50.0% positivo = Mixto
    assert data["sentiment_stats"]["positives_pct"] == 50.0
    assert data["sentiment_stats"]["negatives_pct"] == 50.0
    assert len(data["reviews_classified"]) == 2
    assert data["reviews_classified"][0]["sentiment_predicted"] == "Positivo"
    assert data["reviews_classified"][1]["sentiment_predicted"] == "Negativo"
    assert "game_details" in data
    assert data["game_details"]["developer"] == "Valve"


@patch("routers.games.analizar_reseñas")
def test_badge_endpoint(mock_analizar, client):
    """
    Verifica que el endpoint '/api/games/{app_id}/badge' devuelva una imagen SVG.
    """
    mock_analizar.return_value = {
        "recommendation_level": "Extremadamente Recomendado",
        "sentiment_stats": {"positives_pct": 92.5}
    }
    response = client.get("/api/games/400/badge")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "svg" in response.text
    assert "Ext. Recomendado" in response.text
