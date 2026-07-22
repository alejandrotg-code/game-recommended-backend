import os
import re
import logging
import joblib

logger = logging.getLogger(__name__)

# Determinamos la ruta del modelo relativa a este archivo (services/sentiment.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "modelo_sentimiento.joblib")

class SentimentService:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.vectorizador = None
        self.modelo = None
        
        # Patrones de limpieza de texto idénticos a los del entrenamiento
        self.re_menciones = re.compile(r'@\w+')
        self.re_hashtags = re.compile(r'#')
        self.re_puntuacion = re.compile(r'[^\w\s]')
        self.re_numeros = re.compile(r'\d+')
        
        self.load_model()

    def load_model(self):
        try:
            if os.path.exists(self.model_path):
                componentes = joblib.load(self.model_path)
                self.vectorizador = componentes["vectorizador"]
                self.modelo = componentes["modelo"]
                logger.info("Modelo de sentimiento cargado desde %s", self.model_path)
            else:
                logger.warning("No se encontró el archivo del modelo en: %s", self.model_path)
        except Exception as e:
            logger.error("No se pudo cargar el modelo de sentimiento: %s", e)

    @property
    def model_loaded(self) -> bool:
        return self.modelo is not None and self.vectorizador is not None

    def limpiar_resena(self, texto: str) -> str:
        """Transforma el texto a minúsculas y elimina el ruido de sintaxis."""
        texto = str(texto).lower()
        texto = self.re_menciones.sub('', texto)
        texto = self.re_hashtags.sub('', texto)
        texto = self.re_puntuacion.sub('', texto)
        texto = self.re_numeros.sub('', texto)
        return texto.strip()

    def predecir_sentimientos(self, textos: list) -> list:
        """
        Predice el sentimiento en lote (vectorización + predicción).
        Devuelve una lista de 1 (Positivo) o 0 (Negativo)
        """
        if not self.model_loaded:
            raise ValueError("El modelo de análisis de sentimiento no está disponible en el servidor.")
        
        textos_limpios = [self.limpiar_resena(t) for t in textos]
        X_counts = self.vectorizador.transform(textos_limpios)
        return self.modelo.predict(X_counts).tolist()

# Instancia singleton para ser importada por los routers/controladores
sentiment_service = SentimentService()
