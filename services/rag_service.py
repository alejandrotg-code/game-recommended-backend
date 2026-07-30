import os
import json
import logging
import httpx
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

# Configuración de clientes y modelos desde variables de entorno
groq_api_key = os.getenv("GROQ_API_KEY")
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY", None)

# Inicializar cliente de Qdrant y modelo de Embeddings
qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_groq_llm(model_name: str = "llama-3.1-8b-instant") -> ChatGroq:
    """Retorna cliente de Groq LLM con la API Key configurada."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurada en el entorno.")
    return ChatGroq(temperature=0.2, model_name=model_name, api_key=api_key)

async def translate_es_to_en(query_es: str) -> str:
    """Traduce la consulta del usuario de español a inglés usando Groq de forma instantánea."""
    llm = get_groq_llm("llama-3.1-8b-instant")
    prompt = f"""You are a translator for a video game recommendation engine.
Translate the following user search query from Spanish to English.
Output ONLY the clean English translation, without quotes, explanations or extra text.

Spanish Query: {query_es}
English Translation:"""
    try:
        res = llm.invoke(prompt)
        translated = res.content.strip()
        logger.info(f"Traducción Groq ES -> EN: '{query_es}' -> '{translated}'")
        return translated
    except Exception as e:
        logger.warning(f"Error traduciendo query con Groq: {e}. Se usará query original.")
        return query_es

async def recommend_games_rag(query_es: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Pipeline RAG completo:
    1. Traduce consulta de español a inglés.
    2. Convierte la consulta a vector y busca en Qdrant (semántica).
    3. Genera una recomendación estructurada y razonada en español con Groq Llama 3.
    """
    # 1. Traducir consulta al inglés para maximizar precisión semántica en el catálogo de Steam
    query_en = await translate_es_to_en(query_es)

    # 2. Búsqueda por Similitud de Vectores en Qdrant
    vector_query = embedding_model.encode(query_en).tolist()
    
    try:
        if hasattr(qdrant_client, "query_points"):
            res = qdrant_client.query_points(
                collection_name="steam_games",
                query=vector_query,
                limit=top_k
            )
            search_results = res.points
        else:
            search_results = qdrant_client.search(
                collection_name="steam_games",
                query_vector=vector_query,
                limit=top_k
            )
    except Exception as e:
        logger.error(f"Error consultando Qdrant: {e}")
        raise RuntimeError(f"No se pudo consultar la base de datos vectorial Qdrant: {e}")

    games_found = [hit.payload for hit in search_results if hasattr(hit, "payload")]

    if not games_found:
        return {
            "query_es": query_es,
            "query_en": query_en,
            "summary": "No se encontraron juegos que coincidan con tu búsqueda.",
            "games": []
        }

    # 3. Construir Prompt para Groq (Llama 3) para generar recomendación en español
    llm = get_groq_llm("llama-3.1-8b-instant")
    
    context_games_text = ""
    for idx, g in enumerate(games_found, 1):
        context_games_text += f"\nJuego {idx}:\n- Título: {g.get('name')}\n- AppID: {g.get('app_id')}\n- Géneros: {g.get('genres')}\n- Etiquetas: {g.get('tags')}\n- Descripción: {g.get('about')[:300]}...\n"

    prompt = f"""Eres un recomendador experto de videojuegos muy empático y entusiasta.
El usuario ha expresado en español la siguiente búsqueda/estado de ánimo: "{query_es}" (traducido a inglés como: "{query_en}").

A continuación tienes los mejores {len(games_found)} juegos encontrados semánticamente en el catálogo de Steam:
{context_games_text}

Tu objetivo:
1. Escribe un resumen inicial breve y cordial en español en sintonía con el estado de ánimo o petición del usuario.
2. Para CADA juego de la lista, explica brevemente en 2 frases por qué encaja perfectamente con su solicitud.

Responde ÚNICAMENTE en idioma ESPAÑOL con la siguiente estructura JSON estricta (sin bloques ```json):
{{
  "resumen": "Tu resumen empático en español aquí",
  "razones": {{
    "APP_ID_1": "Razón en español para el juego 1",
    "APP_ID_2": "Razón en español para el juego 2"
  }}
}}
"""

    try:
        res = llm.invoke(prompt)
        raw_output = res.content.strip()
        
        # Limpieza por si devuelve bloques markdown
        if raw_output.startswith("```json"):
            raw_output = raw_output.replace("```json", "").replace("```", "").strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output.replace("```", "").strip()

        parsed_ia = json.loads(raw_output)
        summary_es = parsed_ia.get("resumen", "Aquí tienes las mejores opciones encontradas:")
        razones_map = parsed_ia.get("razones", {})
    except Exception as e:
        logger.warning(f"Error parseando JSON de Groq: {e}. Generando fallback texto.")
        summary_es = f"Hemos encontrado {len(games_found)} recomendaciones para ti basadas en '{query_es}'."
        razones_map = {}

    # Enriquecer lista final de juegos con razones de la IA e imagen oficial de Steam CDN
    final_games = []
    for g in games_found:
        app_id_str = str(g.get("app_id"))
        reason = razones_map.get(app_id_str, g.get("about", "")[:180] + "...")
        
        header_img = g.get("header_image")
        if not header_img or not str(header_img).startswith("http"):
            header_img = f"https://cdn.akamai.steamstatic.com/steam/apps/{g.get('app_id')}/header.jpg"

        final_games.append({
            "app_id": g.get("app_id"),
            "name": g.get("name"),
            "price": g.get("price"),
            "header_image": header_img,
            "genres": g.get("genres"),
            "tags": g.get("tags"),
            "reason_ai": reason
        })

    return {
        "query_es": query_es,
        "query_en": query_en,
        "summary": summary_es,
        "games": final_games
    }
