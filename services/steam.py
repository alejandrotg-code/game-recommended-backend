import logging
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Cliente HTTP reutilizable con pooling de conexiones.
# Se cierra limpiamente al apagar la aplicación via lifespan (app.py).
_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Devuelve el cliente HTTP compartido. Lo crea bajo demanda."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
    return _http_client


async def close_http_client():
    """Cierra el cliente HTTP. Llamar al apagar la app."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def buscar_juegos_steam(term: str) -> dict:
    """Busca juegos en la API pública de Steam utilizando un término."""
    url = "https://store.steampowered.com/api/storesearch/"
    params = {"term": term, "l": "spanish", "cc": "ES"}

    try:
        client = await get_http_client()
        response = await client.get(url, params=params)

        if response.status_code != 200:
            logger.error("Steam storesearch devolvió HTTP %d para '%s'", response.status_code, term)
            raise HTTPException(
                status_code=502,
                detail=f"Error al conectar con la API de Steam (HTTP {response.status_code})",
            )

        data = response.json()
        items = data.get("items", [])

        resultados = []
        for item in items:
            price_data = item.get("price")
            precio_texto = "Gratis / No disponible"
            if price_data:
                try:
                    currency = price_data.get("currency", "EUR")
                    final_price = price_data.get("final", 0) / 100.0
                    precio_texto = f"{final_price:.2f} {currency}"
                except (TypeError, ValueError):
                    logger.debug("No se pudo parsear precio para item %s", item.get("id"))

            resultados.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "price": precio_texto,
                "image": item.get("tiny_image"),
                "metascore": item.get("metascore") or "N/A",
            })

            if len(resultados) >= 15:
                break

        return {
            "query": term,
            "total_found": len(resultados),
            "games": resultados,
        }

    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error("Fallo de conexión con Steam storesearch: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Fallo de conexión con la API de Steam: {str(e)}",
        )


async def obtener_reseñas_steam(app_id: int, limit: int) -> list:
    """Obtiene la lista de reseñas en español desde la API pública de Steam."""
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    params = {
        "json": 1,
        "filter": "all",
        "language": "spanish",
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": limit,
    }

    try:
        client = await get_http_client()
        response = await client.get(url, params=params)

        if response.status_code != 200:
            logger.error("Steam appreviews devolvió HTTP %d para app_id=%d", response.status_code, app_id)
            raise HTTPException(
                status_code=502,
                detail=f"Error al obtener reseñas de Steam (HTTP {response.status_code})",
            )

        data = response.json()
        if not data.get("success", False):
            raise HTTPException(
                status_code=404,
                detail="No se pudo obtener información del juego o el AppID no existe.",
            )

        return data.get("reviews", [])

    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error("Fallo de conexión al solicitar reseñas para app_id=%d: %s", app_id, e)
        raise HTTPException(
            status_code=503,
            detail=f"Fallo de conexión al solicitar reseñas a Steam: {str(e)}",
        )


async def obtener_detalles_juego(app_id: int) -> dict:
    """Obtiene géneros, desarrollador, fecha de lanzamiento y precio de Steam."""
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": app_id, "l": "spanish", "cc": "ES"}

    try:
        client = await get_http_client()
        response = await client.get(url, params=params)

        if response.status_code != 200:
            logger.warning("appdetails devolvió HTTP %d para app_id=%d", response.status_code, app_id)
            return {}

        data = response.json()
        app_data = data.get(str(app_id), {})
        if not app_data.get("success", False):
            logger.debug("appdetails success=false para app_id=%d (juego no encontrado o sin datos)", app_id)
            return {}

        data_info = app_data.get("data", {})

        developers = data_info.get("developers", [])
        desarrollador = developers[0] if developers else "Desconocido"

        genres_list = data_info.get("genres", [])
        generos = [g.get("description") for g in genres_list if g.get("description")]

        release_date = data_info.get("release_date", {})
        fecha_lanzamiento = release_date.get("date", "Desconocido")

        price_overview = data_info.get("price_overview", {})
        precio = price_overview.get("final_formatted")
        if not precio:
            is_free = data_info.get("is_free", False)
            precio = "Gratis" if is_free else "No disponible"

        metacritic = data_info.get("metacritic", {})
        metascore = metacritic.get("score") or "N/A"

        return {
            "developer": desarrollador,
            "genres": generos,
            "release_date": fecha_lanzamiento,
            "price": precio,
            "metascore": metascore,
        }

    except Exception as e:
        logger.error("Error inesperado al obtener detalles del juego app_id=%d: %s", app_id, e)
        return {}



