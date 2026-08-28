import os
import json
import logging
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from services.steam import buscar_juegos_steam, obtener_detalles_juego

logger = logging.getLogger(__name__)

groq_api_key = os.getenv("GROQ_API_KEY")
groq_model_default = os.getenv("GROQ_MODEL", "groq/compound-mini")


def get_groq_llm(model_name: str = groq_model_default) -> ChatGroq:
    """Retorna cliente de Groq LLM con la API Key configurada."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurada en el entorno.")
    return ChatGroq(temperature=0.2, model_name=model_name, api_key=api_key)


async def extract_search_terms_and_famous_games(query_es: str) -> Dict[str, Any]:
    """
    Traduce la consulta del usuario, extrae términos de búsqueda para Steam
    y propone una lista de títulos famosos de referencia del catálogo de Steam.
    """
    llm = get_groq_llm()
    prompt = f"""You are a video game expert and Steam catalog search optimizer.
Given the user query in Spanish: "{query_es}"

Task:
1. Translate and optimize the request into 2 to 4 clean English search keywords or short terms suitable for searching on Steam (e.g., ["farm", "farming", "cozy", "relaxing"]).
2. Provide a list of 6 to 10 famous, highly popular benchmark video games available on Steam that perfectly match this mood/genre (e.g., if user asks for relaxing farming games, include "Stardew Valley", "Slime Rancher", "Farm Together 2", "Coral Island", "Fae Farm", "Sun Haven", "Roots of Pacha").

Output ONLY a strict JSON object with no markdown backticks, quotes or extra commentary:
{{
  "query_en": "primary search term",
  "keywords": ["term1", "term2", "term3"],
  "famous_games": ["Game Title 1", "Game Title 2", "Game Title 3", "Game Title 4", "Game Title 5"]
}}
"""
    try:
        res = await llm.ainvoke(prompt)
        raw = res.content.strip()
        if raw.startswith("```json"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        elif raw.startswith("```"):
            raw = raw.replace("```", "").strip()

        data = json.loads(raw)
        logger.info(f"Groq extracción exitosa para '{query_es}': keywords={data.get('keywords')}, famous={data.get('famous_games')}")
        return data
    except Exception as e:
        logger.warning(f"Error extrayendo datos con Groq: {e}. Se usará fallback.")
        return {
            "query_en": query_es,
            "keywords": [query_es],
            "famous_games": []
        }


async def translate_and_extract_search_term(query_es: str) -> str:
    """Función de compatibilidad para extraer el término primario en inglés."""
    info = await extract_search_terms_and_famous_games(query_es)
    return info.get("query_en", query_es)


async def recommend_games_rag(query_es: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Pipeline de recomendación híbrido RAG usando la API de Steam en tiempo real + Groq:
    1. Groq analiza la consulta, genera palabras clave optimizadas y sugiere títulos emblemáticos del género.
    2. Consulta en tiempo real la API oficial de Steam para obtener datos en vivo de los títulos sugeridos y de las búsquedas.
    3. Construye un pool rico de candidatos que incluye grandes éxitos reconocidos (como Stardew Valley) junto con novedades de Steam.
    4. Groq selecciona los mejores `top_k` y redacta un resumen empático en español con razones personalizadas.
    """
    # 1. Obtener palabras clave y juegos famosos vía Groq
    info = await extract_search_terms_and_famous_games(query_es)
    query_en = info.get("query_en", query_es)
    keywords = info.get("keywords", [query_en])
    famous_games_suggested = info.get("famous_games", [])

    candidate_map: Dict[int, Dict[str, Any]] = {}

    # 2a. Buscar los títulos famosos en tiempo real en Steam para garantizar su disponibilidad e ID
    for title in famous_games_suggested:
        try:
            res = await buscar_juegos_steam(term=title)
            games = res.get("games", [])
            if games:
                first = games[0]
                app_id = first.get("id")
                if app_id and app_id not in candidate_map:
                    candidate_map[app_id] = first
        except Exception as e:
            logger.debug(f"No se pudo obtener '{title}' de Steam: {e}")

    # 2b. Buscar por palabras clave en la API de Steam
    for kw in keywords + [query_en, query_es]:
        if len(candidate_map) >= max(top_k + 10, 30):
            break
        try:
            res = await buscar_juegos_steam(term=kw)
            for g in res.get("games", []):
                app_id = g.get("id")
                if app_id and app_id not in candidate_map:
                    candidate_map[app_id] = g
        except Exception as e:
            logger.debug(f"No se pudieron obtener resultados para palabra clave '{kw}': {e}")

    candidate_games = list(candidate_map.values())

    if not candidate_games:
        return {
            "query_es": query_es,
            "query_en": query_en,
            "summary": "No se encontraron juegos en tiempo real en Steam que coincidan con tu búsqueda.",
            "games": []
        }

    # Limitar el pool final enviado a Groq para análisis
    candidate_games = candidate_games[:max(top_k + 10, 30)]

    # 3. Construir Prompt para Groq para analizar y seleccionar los mejores top_k juegos
    llm = get_groq_llm()
    
    context_games_text = ""
    for idx, g in enumerate(candidate_games, 1):
        context_games_text += f"\nJuego {idx}:\n- AppID: {g.get('id')}\n- Título: {g.get('name')}\n- Precio: {g.get('price')}\n- Metascore: {g.get('metascore')}\n"

    prompt = f"""Eres un recomendador experto de videojuegos empático, entusiasta e informado.
El usuario ha expresado en español la siguiente búsqueda o estado de ánimo: "{query_es}" (búsqueda procesada: "{query_en}").

A continuación tienes una lista en tiempo real de juegos devueltos directamente por la API de Steam (incluye éxitos referentes del género y opciones recientes):
{context_games_text}

Tu objetivo:
1. Escribe un resumen inicial breve y cordial en español (2-3 frases) en sintonía con el deseo/estado de ánimo del usuario.
2. Selecciona los mejores {min(top_k, len(candidate_games))} juegos de la lista, asegurándote de priorizar los títulos más relevantes, queridos y destacados para la preferencia del usuario. Para CADA UNO, explica brevemente en 2 frases por qué encaja perfectamente con su solicitud.

Responde ÚNICAMENTE en idioma ESPAÑOL con la siguiente estructura JSON estricta (sin bloques ```json ni texto adicional):
{{
  "resumen": "Tu resumen empático en español aquí",
  "razones": {{
    "APP_ID_COMO_STRING": "Razón en español para el juego"
  }}
}}
"""

    try:
        res = await llm.ainvoke(prompt)
        raw_output = res.content.strip()
        
        # Limpieza de markdown
        if raw_output.startswith("```json"):
            raw_output = raw_output.replace("```json", "").replace("```", "").strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output.replace("```", "").strip()

        parsed_ia = json.loads(raw_output)
        summary_es = parsed_ia.get("resumen", "Aquí tienes las mejores opciones encontradas en Steam:")
        razones_map = parsed_ia.get("razones", {})
    except Exception as e:
        logger.warning(f"Error parseando respuesta JSON de Groq: {e}. Generando fallback.")
        summary_es = f"Hemos encontrado {len(candidate_games)} recomendaciones en tiempo real desde la API de Steam para tu búsqueda '{query_es}'."
        razones_map = {}

    # 4. Construir la lista final de juegos enriquecidos
    final_games = []
    
    selected_app_ids = [str(k) for k in razones_map.keys()]
    
    chosen_candidates = []
    if selected_app_ids:
        for app_id_str in selected_app_ids:
            found = next((g for g in candidate_games if str(g.get("id")) == app_id_str), None)
            if found and found not in chosen_candidates:
                chosen_candidates.append(found)

    for g in candidate_games:
        if len(chosen_candidates) >= top_k:
            break
        if g not in chosen_candidates:
            chosen_candidates.append(g)

    for g in chosen_candidates[:top_k]:
        app_id = g.get("id")
        app_id_str = str(app_id)
        reason = razones_map.get(app_id_str, f"{g.get('name')} destaca en el catálogo de Steam y coincide con tu búsqueda.")
        
        details = await obtener_detalles_juego(app_id=app_id) if app_id else {}
        genres_str = ", ".join(details.get("genres", [])) if details.get("genres") else "General"
        
        header_img = g.get("image")
        if not header_img or not str(header_img).startswith("http"):
            header_img = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

        final_games.append({
            "app_id": app_id,
            "name": g.get("name"),
            "price": g.get("price", details.get("price", "N/A")),
            "header_image": header_img,
            "genres": genres_str,
            "tags": genres_str,
            "reason_ai": reason
        })

    return {
        "query_es": query_es,
        "query_en": query_en,
        "summary": summary_es,
        "games": final_games
    }
