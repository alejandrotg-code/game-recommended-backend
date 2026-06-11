import httpx
from fastapi import HTTPException

async def buscar_juegos_steam(term: str) -> dict:
    """
    Busca juegos en la API pública de Steam utilizando un término.
    """
    url = "https://store.steampowered.com/api/storesearch/"
    params = {
        "term": term,
        "l": "spanish",
        "cc": "ES"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
        if response.status_code != 200:
            raise HTTPException(
                status_code=502, 
                detail=f"Error al conectar con la API de Steam (HTTP {response.status_code})"
            )
        
        data = response.json()
        items = data.get("items", [])
        
        resultados = []
        for item in items:
            # Procesar el precio de forma segura (Steam storesearch a veces no incluye el campo o es gratis)
            price_data = item.get("price")
            precio_texto = "Gratis / No disponible"
            if price_data:
                try:
                    currency = price_data.get("currency", "EUR")
                    final_price = price_data.get("final", 0) / 100.0
                    precio_texto = f"{final_price:.2f} {currency}"
                except Exception:
                    pass
            
            resultados.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "price": precio_texto,
                "image": item.get("tiny_image"),
                "metascore": item.get("metascore") or "N/A"
            })
            
            # Limitar a máximo 15 juegos para proteger la transferencia de datos y evitar abusos
            if len(resultados) >= 15:
                break
            
        return {
            "query": term,
            "total_found": len(resultados),
            "games": resultados
        }
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Fallo de conexión con la API de Steam: {str(e)}"
        )

async def obtener_reseñas_steam(app_id: int, limit: int) -> list:
    """
    Obtiene la lista de reseñas en español directamente desde la API pública de reseñas de Steam.
    """
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    params = {
        "json": 1,
        "filter": "all",
        "language": "spanish",
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": limit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
        if response.status_code != 200:
            raise HTTPException(
                status_code=502, 
                detail=f"Error al obtener reseñas de Steam (HTTP {response.status_code})"
            )
        
        data = response.json()
        if not data.get("success", False):
            raise HTTPException(
                status_code=404, 
                detail="No se pudo obtener información del juego o el AppID no existe."
            )
        
        return data.get("reviews", [])
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Fallo de conexión al solicitar reseñas a Steam: {str(e)}"
        )


async def obtener_detalles_juego(app_id: int) -> dict:
    """
    Obtiene géneros, desarrollador, fecha de lanzamiento y precio de Steam
    usando la API de appdetails de Steam.
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": app_id,
        "l": "spanish",
        "cc": "ES"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
        if response.status_code != 200:
            return {}
            
        data = response.json()
        app_data = data.get(str(app_id), {})
        if not app_data.get("success", False):
            return {}
            
        data_info = app_data.get("data", {})
        
        # Desarrollador
        developers = data_info.get("developers", [])
        desarrollador = developers[0] if developers else "Desconocido"
        
        # Géneros
        genres_list = data_info.get("genres", [])
        generos = [g.get("description") for g in genres_list if g.get("description")]
        
        # Fecha de lanzamiento
        release_date = data_info.get("release_date", {})
        fecha_lanzamiento = release_date.get("date", "Desconocido")
        
        # Precio actual
        price_overview = data_info.get("price_overview", {})
        precio = price_overview.get("final_formatted")
        if not precio:
            is_free = data_info.get("is_free", False)
            precio = "Gratis" if is_free else "No disponible"
            
        return {
            "developer": desarrollador,
            "genres": generos,
            "release_date": fecha_lanzamiento,
            "price": precio
        }
    except Exception:
        return {}

