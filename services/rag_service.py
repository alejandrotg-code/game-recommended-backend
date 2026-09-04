import os
import json
import logging
import asyncio
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from services.steam import buscar_juegos_steam, obtener_detalles_juego

logger = logging.getLogger(__name__)

groq_api_key = os.getenv("GROQ_API_KEY")
groq_model_default = os.getenv("GROQ_MODEL", "groq/compound-mini")


def sanitize_prompt_input(text: str) -> str:
    """Limpia la entrada del usuario para prevenir inyección de prompts."""
    return text.replace('"', '\\"').replace('\n', ' ').strip()


def get_groq_llm(model_name: str = groq_model_default) -> ChatGroq:
    """Retorna cliente de Groq LLM con la API Key configurada y timeout razonable."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurada en el entorno.")
    return ChatGroq(temperature=0.2, model_name=model_name, api_key=api_key, request_timeout=15.0)


async def extract_search_terms_and_famous_games(query_es: str) -> Dict[str, Any]:
    """
    Traduce la consulta del usuario, extrae términos de búsqueda para Steam
    y propone una lista de títulos famosos de referencia del catálogo de Steam.
    """
    llm = get_groq_llm()
    clean_query = sanitize_prompt_input(query_es)

    prompt = f"""You are a video game expert and Steam catalog search optimizer.
Given the user query in Spanish: "{clean_query}"

Task:
1. Translate and optimize the request into 2 to 4 clean English search keywords or short terms suitable for searching on Steam (e.g., ["farm", "farming", "cozy", "relaxing"]).
2. Provide a list of 6 to 10 famous, highly popular benchmark video games available on Steam that perfectly match this mood/genre.

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


async def _safe_buscar_juegos(term: str) -> List[Dict[str, Any]]:
    """Helper para buscar en Steam evitando elevar excepciones no controladas."""
    try:
        res = await buscar_juegos_steam(term=term)
        return res.get("games", [])
    except Exception as e:
        logger.debug(f"Error en búsqueda Steam para '{term}': {e}")
        return []


async def recommend_games_rag(query_es: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Pipeline de recomendación híbrido RAG usando la API de Steam en tiempo real + Groq:
    1. Groq analiza la consulta, genera palabras clave optimizadas y sugiere títulos emblemáticos.
    2. Consulta en paralelo la API oficial de Steam para obtener datos en vivo.
    3. Groq selecciona los mejores `top_k` y redacta un resumen empático en español.
    """
    # 1. Obtener palabras clave y juegos famosos vía Groq
    info = await extract_search_terms_and_famous_games(query_es)
    query_en = info.get("query_en", query_es)
    keywords = info.get("keywords", [query_en])
    famous_games_suggested = info.get("famous_games", [])

    candidate_map: Dict[int, Dict[str, Any]] = {}

    # 2. Consultar Steam en PARALELO para juegos famosos y palabras clave
    all_search_terms = list(dict.fromkeys(famous_games_suggested + keywords + [query_en, query_es]))
    search_tasks = [_safe_buscar_juegos(term) for term in all_search_terms]
    search_results = await asyncio.gather(*search_tasks)

    for games in search_results:
        for g in games:
            app_id = g.get("id")
            if app_id and app_id not in candidate_map:
                candidate_map[app_id] = g

    candidate_games = list(candidate_map.values())

    if not candidate_games:
        return {
            "query_es": query_es,
            "query_en": query_en,
            "summary": "No se encontraron juegos en tiempo real en Steam que coincidan con tu búsqueda.",
            "games": []
        }

    candidate_games = candidate_games[:max(top_k + 10, 30)]

    # 3. Construir Prompt para Groq para analizar y seleccionar los mejores top_k juegos
    llm = get_groq_llm()
    clean_query = sanitize_prompt_input(query_es)
    clean_query_en = sanitize_prompt_input(query_en)
    
    context_games_text = ""
    for idx, g in enumerate(candidate_games, 1):
        context_games_text += f"\nJuego {idx}:\n- AppID: {g.get('id')}\n- Título: {g.get('name')}\n- Precio: {g.get('price')}\n- Metascore: {g.get('metascore')}\n"

    prompt = f"""Eres un recomendador experto de videojuegos empático, entusiasta e informado.
El usuario ha expresado en español la siguiente búsqueda o estado de ánimo: "{clean_query}" (búsqueda procesada: "{clean_query_en}").

A continuación tienes una lista en tiempo real de juegos devueltos directamente por la API de Steam:
{context_games_text}

Tu objetivo:
1. Escribe un resumen inicial breve y cordial en español (2-3 frases) en sintonía con el deseo del usuario.
2. Selecciona los mejores {min(top_k, len(candidate_games))} juegos de la lista. Para CADA UNO, explica brevemente en 2 frases por qué encaja.

Responde ÚNICAMENTE en idioma ESPAÑOL con la siguiente estructura JSON estricta (sin bloques ```json ni texto adicional):
{{
  "resumen": "Tu resumen empático en español aquí",
  "razones": {{
    "APP_ID_O_TITULO": "Razón en español para el juego"
  }}
}}
"""

    try:
        res = await llm.ainvoke(prompt)
        raw_output = res.content.strip()
        
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

    # 4. Construir la lista final de juegos con coincidencia robusta de claves
    chosen_candidates = []
    
    # Mapeo flexible: intenta coincidir por AppID o por nombre de juego
    for key, reason in razones_map.items():
        key_str = str(key).strip().lower()
        found = next(
            (g for g in candidate_games if str(g.get("id")) == key_str or str(g.get("name", "")).strip().lower() == key_str),
            None
        )
        if found and found not in chosen_candidates:
            chosen_candidates.append(found)

    for g in candidate_games:
        if len(chosen_candidates) >= top_k:
            break
        if g not in chosen_candidates:
            chosen_candidates.append(g)

    selected_top_games = chosen_candidates[:top_k]

    # Obtener detalles de juegos en PARALELO
    details_tasks = [obtener_detalles_juego(app_id=g.get("id")) if g.get("id") else asyncio.sleep(0, result={}) for g in selected_top_games]
    details_list = await asyncio.gather(*details_tasks)

    final_games = []
    for g, details in zip(selected_top_games, details_list):
        app_id = g.get("id")
        app_id_str = str(app_id)
        
        # Buscar razón en razones_map por AppID o Nombre
        reason = razones_map.get(app_id_str) or razones_map.get(str(g.get("name"))) or razones_map.get(g.get("name"))
        if not reason:
            reason = f"{g.get('name')} destaca en el catálogo de Steam y coincide con tu búsqueda."

        genres_list = details.get("genres", []) if isinstance(details, dict) else []
        genres_str = ", ".join(genres_list) if genres_list else "General"
        
        header_img = g.get("image")
        if not header_img or not str(header_img).startswith("http"):
            header_img = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

        final_games.append({
            "app_id": app_id,
            "name": g.get("name"),
            "price": g.get("price", details.get("price", "N/A") if isinstance(details, dict) else "N/A"),
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
