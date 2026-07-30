import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar variables de entorno
env = os.getenv("ENV", "development")
load_dotenv(f".env.{env}", override=True)
if os.path.exists(".env.production"):
    load_dotenv(".env.production", override=True)

# ── Logging ──────────────────────────────────────────────────
# En development: todo visible, formato legible
# En production: solo warnings+, formato con timestamp
log_level = logging.DEBUG if env == "development" else logging.WARNING
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from middleware import RateLimitMiddleware
from services import sentiment_service
from services.steam import close_http_client
from routers import games_router, health_router, rag_router

logger = logging.getLogger(__name__)

# ── Configuración desde entorno ──────────────────────────────
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Gestiona el ciclo de vida de la app: startup y shutdown."""
    # Startup: cargar modelo de sentimiento en el arranque
    if not sentiment_service.model_loaded:
        logger.info("Cargando modelo de sentimiento en el arranque...")
        sentiment_service.load_model()
    yield
    # Shutdown: cerrar el cliente HTTP compartido
    await close_http_client()


app = FastAPI(
    title="Steam Reviews Recommender API",
    description="API para buscar juegos de Steam y analizar el sentimiento de sus reseñas en español utilizando un modelo de Machine Learning.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aplicar middleware de rate limit
app.add_middleware(RateLimitMiddleware, max_requests=RATE_LIMIT, window_seconds=RATE_WINDOW)

# Registrar routers
app.include_router(games_router)
app.include_router(health_router)
app.include_router(rag_router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Steam Reviews Recommender API funcionando correctamente",
        "model_loaded": sentiment_service.model_loaded,
    }
