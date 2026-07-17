from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware import RateLimitMiddleware
from services import sentiment_service
from routers import games_router, health_router

app = FastAPI(
    title="Steam Reviews Recommender API",
    description="API para buscar juegos de Steam y analizar el sentimiento de sus reseñas en español utilizando un modelo de Machine Learning.",
    version="1.0.0"
)

# Configurar middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Aplicar middleware de rate limit (máximo 30 peticiones por minuto por IP)
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)

# Registrar routers
app.include_router(games_router)
app.include_router(health_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Steam Reviews Recommender API funcionando correctamente",
        "model_loaded": sentiment_service.model_loaded
    }
