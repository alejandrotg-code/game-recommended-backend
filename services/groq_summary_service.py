import os
import json
import logging
from typing import List, Dict, Any
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


def get_groq_summary_llm() -> ChatGroq | None:
    """
    Retorna el cliente de Groq LLM utilizando la API Key dedicada GROQ_SUMMARY_API_KEY.
    Si no está presente, cae en GROQ_API_KEY como respaldo.
    """
    api_key = os.getenv("GROQ_SUMMARY_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_api_key":
        return None

    # Modelo ultra-rápido soportado por Groq Cloud
    model_name = os.getenv("GROQ_SUMMARY_MODEL", "openai/gpt-oss-120b")
    return ChatGroq(temperature=0.3, model_name=model_name, api_key=api_key, request_timeout=15.0)


async def generate_game_summary_groq(
    game_name: str,
    app_id: int,
    recommendation_level: str,
    reviews_texts: List[str],
    game_details: Dict[str, Any],
) -> Dict[str, Any] | None:
    """
    Genera un informe periodístico estructurado categorizado en:
    - Resumen Ejecutivo
    - Historia y Narrativa
    - Jugabilidad y Combate
    - Rendimiento, Bugs y Estado Técnico
    - Pros y Contras
    - Perfil del Jugador Ideal
    """
    llm = get_groq_summary_llm()
    if llm is None:
        logger.info(f"GROQ_SUMMARY_API_KEY no configurada. Se omite la síntesis Groq para AppID {app_id}.")
        return None

    try:
        reviews_snippet = "\n- ".join([t[:280] for t in reviews_texts[:15] if t])
        genres = ", ".join(game_details.get("genres", [])) if game_details else "Videojuego"
        developer = game_details.get("developer", "Desconocido") if game_details else "Desconocido"

        prompt = f"""Eres un periodista y crítico experto de videojuegos.
Analiza la muestra de opiniones reales de la comunidad de Steam para el juego "{game_name}" (Desarrollador: {developer}, Géneros: {genres}).
El veredicto global calculado es: "{recommendation_level}".

Muestra de reseñas reales en español de los usuarios:
- {reviews_snippet}

Instrucciones:
Analiza y sintetiza las opiniones de la comunidad en 4 áreas clave.
Responde ÚNICAMENTE con un objeto JSON estricto (sin bloques ```json ni texto adicional):
{{
  "executive_summary": "Resumen periodístico claro en 2 o 3 frases sobre la percepción global del juego.",
  "story_summary": "Resumen de lo que dicen las reseñas sobre la historia, el lore o la narrativa.",
  "gameplay_summary": "Resumen sobre el combate, controles, mecánicas y diversión jugable.",
  "tech_and_bugs_summary": "Resumen sobre el rendimiento en PC, optimización, caídas de FPS o bugs reportados.",
  "pros": ["Punto fuerte destacado 1", "Punto fuerte destacado 2", "Punto fuerte destacado 3"],
  "cons": ["Queja o punto débil 1", "Queja o punto débil 2"],
  "target_audience": "Una frase clara explicando para qué tipo de jugador es ideal este videojuego."
}}
"""
        res = await llm.ainvoke(prompt)
        raw_output = res.content.strip()

        if raw_output.startswith("```json"):
            raw_output = raw_output.replace("```json", "").replace("```", "").strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output.replace("```", "").strip()

        data = json.loads(raw_output)
        return {
            "executive_summary": data.get("executive_summary", ""),
            "story_summary": data.get("story_summary", ""),
            "gameplay_summary": data.get("gameplay_summary", ""),
            "tech_and_bugs_summary": data.get("tech_and_bugs_summary", ""),
            "pros": data.get("pros", []),
            "cons": data.get("cons", []),
            "target_audience": data.get("target_audience", ""),
        }
    except Exception as e:
        logger.warning(f"Error generando síntesis Groq para {game_name} (AppID {app_id}): {e}")
        return None
