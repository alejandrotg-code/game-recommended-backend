import os
import re
import logging
import joblib
import asyncio
import pandas as pd
import tensorflow as tf
from services.steam import obtener_detalles_juego

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "game_classifier_keras.keras")
MLB_PATH = os.path.join(BASE_DIR, "model", "mlb_classes.joblib")
VECTORIZER_PATH = os.path.join(BASE_DIR, "model", "keras_vectorizer.joblib")
CSV_PATH = os.path.join(BASE_DIR, "model", "dataset_steam_descripciones.csv")

class RecommendationService:
    def __init__(self, auto_load: bool = False):
        self.model = None
        self.mlb = None
        self.vectorizer_data = None
        self.classes = None
        self.games_df = None
        self.load_errors = {}
        if auto_load:
            self.load_assets()

    def load_assets(self):
        try:
            if os.path.exists(MODEL_PATH):
                try:
                    self.model = tf.keras.models.load_model(MODEL_PATH)
                    logger.info("Modelo de Keras cargado desde %s", MODEL_PATH)
                except Exception as e:
                    self.load_errors["model_load_error"] = str(e)
                    logger.error("No se pudo cargar el modelo de Keras: %s", e)
            else:
                self.load_errors["model_missing"] = f"No se encontró el archivo en {MODEL_PATH}"
                logger.warning("No se encontró el modelo de Keras en: %s", MODEL_PATH)

            if os.path.exists(MLB_PATH):
                try:
                    self.mlb = joblib.load(MLB_PATH)
                    self.classes = self.mlb.classes_
                    logger.info("MultiLabelBinarizer cargado desde %s", MLB_PATH)
                except Exception as e:
                    self.load_errors["mlb_load_error"] = str(e)
                    logger.error("No se pudo cargar mlb_classes: %s", e)
            else:
                self.load_errors["mlb_missing"] = f"No se encontró el archivo en {MLB_PATH}"
                logger.warning("No se encontró mlb_classes en: %s", MLB_PATH)

            if os.path.exists(VECTORIZER_PATH):
                try:
                    self.vectorizer_data = joblib.load(VECTORIZER_PATH)
                    logger.info("Vectorizador cargado desde %s", VECTORIZER_PATH)
                except Exception as e:
                    self.load_errors["vectorizer_load_error"] = str(e)
                    logger.error("No se pudo cargar keras_vectorizer: %s", e)
            else:
                self.load_errors["vectorizer_missing"] = f"No se encontró el archivo en {VECTORIZER_PATH}"
                logger.warning("No se encontró keras_vectorizer en: %s", VECTORIZER_PATH)

            if os.path.exists(CSV_PATH):
                try:
                    self.games_df = pd.read_csv(CSV_PATH)
                    logger.info("Catálogo de juegos cargado desde %s (%d juegos)", CSV_PATH, len(self.games_df))
                except Exception as e:
                    self.load_errors["csv_load_error"] = str(e)
                    logger.error("No se pudo cargar el catálogo de juegos: %s", e)
            else:
                self.load_errors["csv_missing"] = f"No se encontró el archivo en {CSV_PATH}"
                logger.warning("No se encontró el catálogo de juegos en: %s", CSV_PATH)

        except Exception as e:
            self.load_errors["general_error"] = str(e)
            logger.error("No se pudieron cargar los componentes de clasificación: %s", e)

    @property
    def ready(self) -> bool:
        return self.model is not None and self.classes is not None

    def clean_description(self, text: str) -> str:
        """Limpia el texto de las descripciones en español."""
        if not text:
            return ""
        text = str(text).lower()
        # Eliminar etiquetas HTML residuales
        text = re.sub(r'<[^>]+>', ' ', text)
        # Mantener solo letras en español, números y espacios básicos
        text = re.sub(r'[^a-záéíóúüñ0-9 ]', ' ', text)
        # Eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def recommend_by_description(self, description: str) -> dict:
        if not self.ready:
            raise ValueError("El clasificador de géneros no está listo o no se cargó correctamente.")

        cleaned = self.clean_description(description)
        input_tensor = tf.constant([cleaned], dtype=tf.string)
        
        # Predecir
        predictions = self.model.predict(input_tensor)[0]
        
        # Mapear géneros y probabilidades
        genre_probs = []
        for genre, prob in zip(self.classes, predictions):
            genre_probs.append({
                "genre": genre,
                "probability": float(prob) * 100
            })
        
        # Ordenar de mayor a menor probabilidad
        genre_probs = sorted(genre_probs, key=lambda x: x["probability"], reverse=True)
        
        # Obtener el género con mayor probabilidad
        top_genre = genre_probs[0]["genre"] if genre_probs else "Acción"
        top_prob = genre_probs[0]["probability"] if genre_probs else 0.0
        
        # Filtrar catálogo local por género para obtener el TOP 10
        games_list = []
        if self.games_df is not None:
            # Buscamos de forma insensible a mayúsculas y minúsculas el género predicho
            matching_df = self.games_df[self.games_df["genres_es"].str.contains(top_genre, case=False, na=False)]
            # Tomamos el TOP 10 de ese género
            top_10_df = matching_df.head(10)
            
            # Obtener detalles adicionales en paralelo desde Steam
            tasks = []
            for _, row in top_10_df.iterrows():
                app_id = int(row["app_id"])
                game_name = str(row["game_name"])
                
                async def fetch_game_info(aid, name):
                    details = await obtener_detalles_juego(aid)
                    return {
                        "id": aid,
                        "name": name,
                        "price": details.get("price", "No disponible"),
                        "image": f"https://cdn.akamai.steamstatic.com/steam/apps/{aid}/header.jpg",
                        "metascore": details.get("metascore", "N/A")
                    }
                tasks.append(fetch_game_info(app_id, game_name))
                
            if tasks:
                games_list = await asyncio.gather(*tasks)
        
        return {
            "cleaned_description": cleaned,
            "predictions": genre_probs,
            "top_genre": top_genre,
            "top_probability": top_prob,
            "steam_games": games_list
        }

recommendation_service = RecommendationService()

