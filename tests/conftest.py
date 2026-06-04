import pytest
import sys, os, re
from unittest.mock import MagicMock, PropertyMock

# Añadimos el backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Mocks de sentiment_service ANTES de importar la app ---
class MockVectorizer:
    def transform(self, texts):
        return texts

class MockPredictionResult:
    def __init__(self, predictions):
        self.predictions = predictions
    def tolist(self):
        return self.predictions

class MockModel:
    def predict(self, counts):
        predictions = []
        for text in counts:
            if any(w in text for w in ["buen","excelente","recomendado","gusto","genial","divertido","juegazo"]):
                predictions.append(1)
            else:
                predictions.append(0)
        return MockPredictionResult(predictions)

class MockSentimentService:
    model_loaded = True
    model_path = "model/mock.joblib"
    vectorizador = MockVectorizer()
    modelo = MockModel()

    def limpiar_resena(self, texto):
        texto = str(texto).lower()
        texto = re.sub(r'@\w+', '', texto)
        texto = re.sub(r'#', '', texto)
        texto = re.sub(r'[^\w\s]', '', texto)
        texto = re.sub(r'\d+', '', texto)
        return texto.strip()

    def predecir_sentimientos(self, textos):
        limpios = [self.limpiar_resena(t) for t in textos]
        return self.modelo.predict(limpios).tolist()

# Parcheamos el singleton antes de que cualquier módulo lo importe
import services.sentiment as _sent_mod
_sent_mod.sentiment_service = MockSentimentService()

from fastapi.testclient import TestClient
from app import app

@pytest.fixture(autouse=True)
def reset_cache():
    """Limpia el caché entre tests."""
    from cachetools import TTLCache
    import services.cache as _cache_mod
    _cache_mod._search_cache = TTLCache(maxsize=200, ttl=300)
    _cache_mod._analyze_cache = TTLCache(maxsize=100, ttl=1800)
    yield

@pytest.fixture
def client():
    return TestClient(app)