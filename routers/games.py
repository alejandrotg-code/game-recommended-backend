from fastapi import APIRouter, Query, HTTPException
from services.steam import buscar_juegos_steam, obtener_reseñas_steam
from services.sentiment import sentiment_service

router = APIRouter()

@router.get("/api/search")
def buscar_juegos(term: str = Query(..., min_length=1, description="Nombre o término de búsqueda del juego")):
    """
    Busca juegos en la API pública de Steam utilizando un término.
    """
    return buscar_juegos_steam(term)

@router.get("/api/analyze/{app_id}")
def analizar_reseñas(
    app_id: int, 
    limit: int = Query(30, ge=5, le=50, description="Cantidad máxima de reseñas a analizar (máximo 50)")
):
    """
    Obtiene las reseñas más recientes en español de un juego en Steam,
    las preprocesa y predice el sentimiento (Positivo o Negativo) de cada una utilizando el modelo.
    """
    if not sentiment_service.model_loaded:
        raise HTTPException(
            status_code=503, 
            detail="El modelo de análisis de sentimiento no está disponible en el servidor."
        )
    
    # 1. Obtener reseñas desde la API pública de Steam
    reviews_raw = obtener_reseñas_steam(app_id, limit)
    
    if not reviews_raw:
        return {
            "app_id": app_id,
            "total_reviews": 0,
            "recommendation_level": "Sin reseñas",
            "sentiment_stats": {
                "positives_pct": 0,
                "negatives_pct": 0
            },
            "steam_voted_up_pct": 0,
            "reviews_classified": []
        }
    
    # 2. Limpieza y preparación de reseñas
    textos_crudos = [r.get("review", "") for r in reviews_raw]
    
    # 3. Predicción del sentimiento en lote (vectorización + predicción)
    try:
        predicciones = sentiment_service.predecir_sentimientos(textos_crudos)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al clasificar el sentimiento de las reseñas: {str(e)}"
        )
    
    # 4. Agrupación y cálculo de estadísticas
    reseñas_clasificadas = []
    positivas_ia = 0
    positivas_steam = 0
    
    for idx, r in enumerate(reviews_raw):
        sentimiento_ia = predicciones[idx]
        voted_up_steam = 1 if r.get("voted_up") else 0
        
        if sentimiento_ia == 1:
            positivas_ia += 1
        if voted_up_steam == 1:
            positivas_steam += 1
            
        reseñas_clasificadas.append({
            "recommendation_id": r.get("recommendationid"),
            "author": r.get("author", {}).get("personaname", "Usuario de Steam"),
            "playtime_forever": r.get("author", {}).get("playtime_forever", 0),
            "review_text": r.get("review", "").strip(),
            "sentiment_predicted": "Positivo" if sentimiento_ia == 1 else "Negativo",
            "voted_up_steam": bool(voted_up_steam)
        })
        
    total_reviews = len(reviews_raw)
    pos_ia_pct = round((positivas_ia / total_reviews) * 100, 2)
    neg_ia_pct = round(100.0 - pos_ia_pct, 2)
    pos_steam_pct = round((positivas_steam / total_reviews) * 100, 2)
    
    # Clasificar la recomendación según el porcentaje de sentimiento positivo de la IA
    if pos_ia_pct >= 80:
        nivel_recomendacion = "Extremadamente Recomendado"
    elif pos_ia_pct >= 60:
        nivel_recomendacion = "Recomendado"
    elif pos_ia_pct >= 40:
        nivel_recomendacion = "Mixto"
    else:
        nivel_recomendacion = "No Recomendado"

        
    return {
        "app_id": app_id,
        "total_reviews_analyzed": total_reviews,
        "recommendation_level": nivel_recomendacion,
        "sentiment_stats": {
            "positives_pct": pos_ia_pct,
            "negatives_pct": neg_ia_pct
        },
        "steam_voted_up_pct": pos_steam_pct,
        "reviews_classified": reseñas_clasificadas
    }
