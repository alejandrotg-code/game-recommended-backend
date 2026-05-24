import pytest
from fastapi.testclient import TestClient
from app import app
from services import sentiment_service

class MockVectorizer:
    def transform(self, texts):
        # Retorna el mismo texto para ser analizado por el modelo mockeado
        return texts

class MockPredictionResult:
    def __init__(self, predictions):
        self.predictions = predictions

    def tolist(self):
        return self.predictions

class MockModel:
    def predict(self, counts):
        # Lógica simple y determinista para las pruebas
        predictions = []
        for text in counts:
            # Si contiene palabras positivas, se predice 1 (Positivo), de lo contrario 0 (Negativo)
            if any(word in text for word in ["buen", "excelente", "recomendado", "gusto", "genial", "divertido", "juegazo"]):
                predictions.append(1)
            else:
                predictions.append(0)
        return MockPredictionResult(predictions)

@pytest.fixture(autouse=True)
def setup_mock_model():
    """
    Fixture que se ejecuta automáticamente para cada test.
    Reemplaza el modelo de ML real por un mock rápido y determinista.
    """
    # Guardamos los componentes originales
    orig_vectorizador = sentiment_service.vectorizador
    orig_modelo = sentiment_service.modelo
    
    # Inyectamos el mock
    sentiment_service.vectorizador = MockVectorizer()
    sentiment_service.modelo = MockModel()
    
    yield
    
    # Restauramos los componentes originales al finalizar el test
    sentiment_service.vectorizador = orig_vectorizador
    sentiment_service.modelo = orig_modelo

@pytest.fixture
def client():
    """
    Fixture que provee un TestClient para realizar llamadas HTTP a la API de FastAPI.
    """
    return TestClient(app)
