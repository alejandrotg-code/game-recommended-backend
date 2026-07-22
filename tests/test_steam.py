import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import httpx
from fastapi import HTTPException
from services.steam import buscar_juegos_steam, obtener_reseñas_steam, obtener_detalles_juego


def _make_mock_client(response):
    """Crea un mock de httpx.AsyncClient que retorna la response dada."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


@patch("services.steam.get_http_client")
def test_buscar_juegos_steam_success(mock_get_client):
    """
    Verifica que la búsqueda de juegos de Steam formatee correctamente los resultados
    cuando la API retorna un estado exitoso (200).
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": 400,
                "name": "Portal",
                "tiny_image": "http://image.url",
                "metascore": 95,
                "price": {
                    "currency": "EUR",
                    "final": 975,
                },
            }
        ]
    }

    mock_get_client.return_value = _make_mock_client(mock_response)
    resultado = asyncio.run(buscar_juegos_steam("Portal"))

    assert resultado["query"] == "Portal"
    assert resultado["total_found"] == 1
    assert len(resultado["games"]) == 1
    assert resultado["games"][0]["id"] == 400
    assert resultado["games"][0]["name"] == "Portal"
    assert resultado["games"][0]["price"] == "9.75 EUR"


@patch("services.steam.get_http_client")
def test_buscar_juegos_steam_api_error(mock_get_client):
    """
    Verifica que la búsqueda lance una excepción HTTP 502 si Steam retorna un error HTTP (ej. 500).
    """
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_get_client.return_value = _make_mock_client(mock_response)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(buscar_juegos_steam("Portal"))
    assert exc_info.value.status_code == 502


@patch("services.steam.get_http_client")
def test_buscar_juegos_steam_connection_error(mock_get_client):
    """
    Verifica que la búsqueda lance una excepción HTTP 503 ante fallos de conexión a la API.
    """
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection timeout"))
    mock_get_client.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(buscar_juegos_steam("Portal"))
    assert exc_info.value.status_code == 503


@patch("services.steam.get_http_client")
def test_obtener_reseñas_steam_success(mock_get_client):
    """
    Verifica que la obtención de reseñas en español funcione correctamente al recibir respuesta de Steam.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "reviews": [
            {
                "recommendationid": "1",
                "author": {"personaname": "Player1", "playtime_forever": 60},
                "review": "Buen juego",
                "voted_up": True,
            }
        ],
    }

    mock_get_client.return_value = _make_mock_client(mock_response)
    reviews = asyncio.run(obtener_reseñas_steam(400, 10))
    assert len(reviews) == 1
    assert reviews[0]["recommendationid"] == "1"
    assert reviews[0]["review"] == "Buen juego"


@patch("services.steam.get_http_client")
def test_obtener_reseñas_steam_invalid_appid(mock_get_client):
    """
    Verifica que se retorne HTTP 404 si el ID del juego no existe en Steam (success=False).
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": False}

    mock_get_client.return_value = _make_mock_client(mock_response)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(obtener_reseñas_steam(999999, 10))
    assert exc_info.value.status_code == 404


@patch("services.steam.get_http_client")
def test_obtener_detalles_juego_returns_empty_on_http_error(mock_get_client):
    """
    Verifica que obtener_detalles_juego devuelva {} sin lanzar excepción ante un error HTTP.
    """
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_get_client.return_value = _make_mock_client(mock_response)
    result = asyncio.run(obtener_detalles_juego(400))
    assert result == {}


@patch("services.steam.get_http_client")
def test_obtener_detalles_juego_returns_empty_on_exception(mock_get_client):
    """
    Verifica que obtener_detalles_juego devuelva {} sin lanzar excepción ante una excepción inesperada.
    """
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
    mock_get_client.return_value = mock_client

    result = asyncio.run(obtener_detalles_juego(400))
    assert result == {}
