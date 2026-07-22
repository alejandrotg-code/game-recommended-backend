from fastapi import APIRouter, Query, HTTPException, Response
from services.steam import buscar_juegos_steam, obtener_reseñas_steam, obtener_detalles_juego
from services.sentiment import sentiment_service
from services.cache import cache_service

router = APIRouter()


def _sanitize_display_name(name: str, max_length: int = 50) -> str:
    """
    Limpia un nombre de usuario para exponerlo de forma segura.
    Elimina caracteres de control, limita la longitud y strip de whitespace.
    """
    # Eliminar caracteres de control (excepto espacios) y normalizar whitespace
    cleaned = "".join(c for c in name if c.isprintable() or c.isspace())
    cleaned = " ".join(cleaned.split())  # colapsar whitespace múltiple
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned if cleaned else "Usuario de Steam"


def generar_badge_svg(recommendation_level: str, positives_pct: float) -> str:
    color_map = {
        "Extremadamente Recomendado": "#10b981",
        "Recomendado": "#3b82f6",
        "Mixto": "#f59e0b",
        "No Recomendado": "#f43f5e",
        "Sin reseñas": "#6b7280"
    }
    color = color_map.get(recommendation_level, "#6b7280")
    
    verdict_short = recommendation_level
    if verdict_short == "Extremadamente Recomendado":
        verdict_short = "Ext. Recomendado"
        
    text_content = f"{verdict_short} ({positives_pct:.0f}%)"
    
    # Ancho del badge dinámico
    text_width = len(text_content) * 7 + 12
    label_width = 75
    total_width = label_width + text_width
    
    label_x = (label_width / 2) * 10
    text_x = (label_width + text_width / 2) * 10
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" viewBox="0 0 {total_width * 10} 200">
  <linearGradient id="g" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width * 10}" height="200" rx="30" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width * 10}" height="200" fill="#555"/>
    <rect x="{label_width * 10}" width="{text_width * 10}" height="200" fill="{color}"/>
    <rect width="{total_width * 10}" height="200" fill="url(#g)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text x="{label_x}" y="140" fill="#010101" fill-opacity=".3">Steam IA</text>
    <text x="{label_x}" y="130">Steam IA</text>
    <text x="{text_x}" y="140" fill="#010101" fill-opacity=".3">{text_content}</text>
    <text x="{text_x}" y="130">{text_content}</text>
  </g>
</svg>"""



@router.get("/api/search")
async def buscar_juegos(term: str = Query(..., min_length=1, description="Nombre o término de búsqueda del juego")):
    """
    Busca juegos en la API pública de Steam utilizando un término.
    Respuestas cacheadas 5 minutos por término (case-insensitive).
    """
    cached = cache_service.get_search(term)
    if cached:
        return cached

    result = await buscar_juegos_steam(term)
    cache_service.set_search(term, result)
    return result


@router.get("/api/analyze/{app_id}")
async def analizar_reseñas(
    app_id: int,
    limit: int = Query(30, ge=5, le=50, description="Cantidad máxima de reseñas a analizar (máximo 50)")
):
    """
    Obtiene las reseñas más recientes en español de un juego en Steam,
    las preprocesa y predice el sentimiento utilizando el modelo.
    Respuestas cacheadas 30 minutos por app_id.

    Nota: el parámetro `limit` no afecta al caché — si el resultado ya está
    cacheado se devuelve directamente independientemente del limit pedido.
    """
    if not sentiment_service.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="El modelo de análisis de sentimiento no está disponible en el servidor."
        )

    cached = cache_service.get_analyze(app_id, limit)
    if cached:
        return cached

    # 1. Obtener reseñas desde la API pública de Steam
    reviews_raw = await obtener_reseñas_steam(app_id, limit)

    # 1.5 Obtener detalles adicionales del juego
    game_details = await obtener_detalles_juego(app_id)

    if not reviews_raw:
        return {
            "app_id": app_id,
            "total_reviews_analyzed": 0,
            "recommendation_level": "Sin reseñas",
            "sentiment_stats": {
                "positives_pct": 0,
                "negatives_pct": 0
            },
            "steam_voted_up_pct": 0,
            "reviews_classified": [],
            "game_details": game_details
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
            "author": _sanitize_display_name(r.get("author", {}).get("personaname", "")),
            "playtime_forever": r.get("author", {}).get("playtime_forever", 0),
            "review_text": r.get("review", "").strip(),
            "sentiment_predicted": "Positivo" if sentimiento_ia == 1 else "Negativo",
            "voted_up_steam": bool(voted_up_steam),
        })

    total_reviews = len(reviews_raw)
    pos_ia_pct = round((positivas_ia / total_reviews) * 100, 2)
    neg_ia_pct = round(100.0 - pos_ia_pct, 2)
    pos_steam_pct = round((positivas_steam / total_reviews) * 100, 2)

    if pos_ia_pct >= 80:
        nivel_recomendacion = "Extremadamente Recomendado"
    elif pos_ia_pct >= 60:
        nivel_recomendacion = "Recomendado"
    elif pos_ia_pct >= 40:
        nivel_recomendacion = "Mixto"
    else:
        nivel_recomendacion = "No Recomendado"

    result = {
        "app_id": app_id,
        "total_reviews_analyzed": total_reviews,
        "recommendation_level": nivel_recomendacion,
        "sentiment_stats": {
            "positives_pct": pos_ia_pct,
            "negatives_pct": neg_ia_pct
        },
        "steam_voted_up_pct": pos_steam_pct,
        "reviews_classified": reseñas_clasificadas,
        "game_details": game_details
    }

    cache_service.set_analyze(app_id, limit, result)
    return result


@router.get("/api/games/{app_id}/badge")
async def obtener_badge(app_id: int):
    """
    Devuelve un SVG embebible con el veredicto y el porcentaje positivo de reseñas.
    Utiliza el caché si está disponible, o realiza el análisis al vuelo de 30 reseñas.
    """
    cached = cache_service.get_analyze(app_id, 30)
    if not cached:
        try:
            cached = await analizar_reseñas(app_id, limit=30)
        except Exception:
            cached = {
                "recommendation_level": "Sin reseñas",
                "sentiment_stats": {"positives_pct": 0.0}
            }
            
    verdict = cached.get("recommendation_level", "Sin reseñas")
    pos_pct = cached.get("sentiment_stats", {}).get("positives_pct", 0.0)
    
    svg_content = generar_badge_svg(verdict, pos_pct)
    
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "max-age=1800, public"
        }
    )


@router.get("/api/recommend")
async def recomendar_juegos(
    description: str = Query(..., min_length=3, description="Descripción del tipo de juego que buscas")
):
    """
    Recibe una descripción de juego en español, predice su género principal usando Keras,
    y devuelve los juegos populares en Steam de ese género.
    """
    try:
        from services import recommendation_service
        if not recommendation_service.ready:
            raise HTTPException(
                status_code=503,
                detail=f"El clasificador de géneros no está cargado o disponible en el servidor. Detalles de carga: {recommendation_service.load_errors}"
            )
        resultado = await recommendation_service.recommend_by_description(description)
        return resultado
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar recomendaciones: {str(e)}"
        )
