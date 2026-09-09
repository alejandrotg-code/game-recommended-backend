import re
import math
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Expresión regular para detectar spam ASCII (dibujos de gatos, símbolos repetitivos, etc.)
RE_ASCII_MEMES = re.compile(r"[░▒▓█▄▀▐▌│┌┐└┘├┤┬┴┼■□▪▫▲▼►◄]", re.UNICODE)
RE_REPETITIVE_CHARS = re.compile(r"(.)\1{5,}")


def is_spam_or_low_substance(review_text: str) -> bool:
    """
    Detecta si una reseña es spam, meme ASCII o carece de sustancia informativa.
    """
    if not review_text or len(review_text.strip()) < 12:
        return True

    # Si contiene símbolos ASCII o patrones de dibujo
    if len(RE_ASCII_MEMES.findall(review_text)) > 3:
        return True

    # Si contiene secuencias repetidas absurdas (ej. "aaaaaaaaa")
    if RE_REPETITIVE_CHARS.search(review_text):
        return True

    # Si son palabras vacías muy cortas tipo "bueno", "malo", "juegazo"
    words = review_text.strip().split()
    if len(words) <= 2 and len(review_text) < 15:
        return True

    return False


def calculate_substance_score(review_text: str, playtime_forever: int) -> float:
    """
    Calcula una puntuación de sustancia informativa basada en la longitud y horas de juego.
    """
    words = len(review_text.split())
    # Premiar reseñas con longitud sustancial (20-150 palabras)
    length_score = min(words / 40.0, 3.0)

    # Horas de juego (escala logarítmica)
    hours = (playtime_forever or 0) / 60.0
    playtime_score = min(math.log10(hours + 1.0), 2.0)

    return length_score + playtime_score


def curate_diverse_reviews(reviews_raw: list, vectorizer, target_limit: int) -> list:
    """
    Curación Inteligente por IA (MMR - Maximal Marginal Relevance):
    1. Filtra spam y memes ASCII.
    2. Aplica muestreo de diversidad semántica por similitud del coseno (TF-IDF).
    3. Devuelve exactamente 'target_limit' reseñas informativas y temáticamente variadas.
    """
    if not reviews_raw:
        return []

    # 1. Filtrar spam y bajo contenido
    clean_pool = [r for r in reviews_raw if not is_spam_or_low_substance(r.get("review", ""))]

    # Fallback si el filtro resulta en una piscina inferior al límite deseado
    if len(clean_pool) < target_limit:
        clean_pool = [r for r in reviews_raw if r.get("review", "").strip()]
        if not clean_pool:
            return reviews_raw[:target_limit]

    if len(clean_pool) <= target_limit:
        return clean_pool

    # 2. Diversificación Semántica usando el vectorizador TF-IDF
    texts = [r.get("review", "").strip() for r in clean_pool]
    substance_scores = [
        calculate_substance_score(r.get("review", ""), r.get("author", {}).get("playtime_forever", 0))
        for r in clean_pool
    ]

    try:
        if vectorizer is not None:
            tfidf_matrix = vectorizer.transform(texts)
            sim_matrix = cosine_similarity(tfidf_matrix)

            selected_indices = []
            first_idx = int(np.argmax(substance_scores))
            selected_indices.append(first_idx)

            while len(selected_indices) < target_limit and len(selected_indices) < len(clean_pool):
                best_next_idx = -1
                best_combined_score = -float("inf")

                for candidate_idx in range(len(clean_pool)):
                    if candidate_idx in selected_indices:
                        continue

                    # Similitud máxima con las ya seleccionadas
                    max_sim = max(sim_matrix[candidate_idx][sel] for sel in selected_indices)
                    diversity_score = 1.0 - max_sim

                    # Puntuación balanceada (60% Sustancia + 40% Novedad Semántica)
                    combined_score = (0.6 * substance_scores[candidate_idx]) + (0.4 * diversity_score * 3.0)

                    if combined_score > best_combined_score:
                        best_combined_score = combined_score
                        best_next_idx = candidate_idx

                if best_next_idx != -1:
                    selected_indices.append(best_next_idx)
                else:
                    break

            return [clean_pool[i] for i in selected_indices]
    except Exception:
        pass

    # Fallback: ordenar por puntuación de sustancia
    clean_pool.sort(
        key=lambda r: calculate_substance_score(
            r.get("review", ""), r.get("author", {}).get("playtime_forever", 0)
        ),
        reverse=True,
    )
    return clean_pool[:target_limit]
