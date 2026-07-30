from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any
from services import rag_service

router = APIRouter(prefix="/api/rag", tags=["Recomendador RAG IA"])

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Búsqueda o estado de ánimo expresado por el usuario en español", example="Un juego indie relajante con buena música para pasar un día duro")
    top_k: int = Field(default=4, ge=1, le=10, description="Número de recomendaciones a devolver")

@router.post("/recommend", response_model=Dict[str, Any])
async def get_rag_recommendation(body: RAGQueryRequest):
    """
    Endpoint RAG:
    1. Traduce la consulta del usuario de español a inglés automáticamente con Groq.
    2. Realiza una búsqueda semántica de alta precisión en Qdrant Vector DB.
    3. Genera una recomendación empática y estructurada en español usando Groq (Llama 3).
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía.")
    
    try:
        result = await rag_service.recommend_games_rag(query_es=body.query, top_k=body.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar recomendación RAG: {str(e)}")
