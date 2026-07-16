import pytest
from fastapi.testclient import TestClient
from app import app
from services import sentiment_service


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
            if any(w in text for w in ["buen", "excelente", "recomendado", "gusto", "genial", "divertido", "juegazo"]):
                predictions.append(1)
            else:
                predictions.append(0)
        return MockPredictionResult(predictions)


@pytest.fixture(autouse=True)
def setup_mock_model():
    """
    Inyecta el mock sobre la instancia real sin reemplazarla, para que
    todos los módulos que ya la importaron reciban el mismo objeto parcheado.
    """
    orig_vectorizador = sentiment_service.vectorizador
    orig_modelo = sentiment_service.modelo

    sentiment_service.vectorizador = MockVectorizer()
    sentiment_service.modelo = MockModel()

    yield

    sentiment_service.vectorizador = orig_vectorizador
    sentiment_service.modelo = orig_modelo


@pytest.fixture(autouse=True)
def reset_cache():
    """Limpia el caché entre tests para evitar contaminación."""
    from cachetools import TTLCache
    import services.cache as _cache_mod
    _cache_mod._search_cache = TTLCache(maxsize=200, ttl=300)
    _cache_mod._analyze_cache = TTLCache(maxsize=100, ttl=1800)
    yield


@pytest.fixture(autouse=True)
def setup_mock_recommendation():
    """Mocks the recommendation service to avoid TF loading/prediction issues during tests."""
    from services.recommendation import recommendation_service
    
    orig_model = recommendation_service.model
    orig_classes = recommendation_service.classes
    orig_recommend = recommendation_service.recommend_by_description

    recommendation_service.model = object()  # dummy truthy value
    recommendation_service.classes = ["Acción", "Aventura", "Disparos", "Relajante", "Rol", "Simulación"]

    async def mock_recommend_by_description(description: str):
        return {
            "cleaned_description": description.lower().strip(),
            "predictions": [
                {"genre": "Acción", "probability": 90.0},
                {"genre": "Aventura", "probability": 10.0}
            ],
            "top_genre": "Acción",
            "top_probability": 90.0,
            "steam_games": [{"id": 10, "name": "Counter-Strike", "price": "Gratis", "image": "img", "metascore": 88}]
        }

    recommendation_service.recommend_by_description = mock_recommend_by_description

    yield

    recommendation_service.model = orig_model
    recommendation_service.classes = orig_classes
    recommendation_service.recommend_by_description = orig_recommend


@pytest.fixture
def client():
    return TestClient(app)