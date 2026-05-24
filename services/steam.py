import requests
from fastapi import HTTPException

def buscar_juegos_steam(term: str) -> dict:
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
        response = requests.get(url, params=params, timeout=10)
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
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Fallo de conexión con la API de Steam: {str(e)}"
        )

def obtener_reseñas_steam(app_id: int, limit: int) -> list:
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
        response = requests.get(url, params=params, timeout=10)
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
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Fallo de conexión al solicitar reseñas a Steam: {str(e)}"
        )
