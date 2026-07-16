# Game Recommended

[![Demo](https://img.shields.io/badge/Demo-En%20Vivo-brightgreen?style=for-the-badge)](https://game-recommended.alejandrotg.es)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)

Un sistema inteligente y moderno diseñado para analizar las reseñas en español de videojuegos en Steam utilizando Procesamiento de Lenguaje Natural (NLP) y Machine Learning para determinar el nivel real de recomendación de los usuarios, además de recomendar nuevos títulos mediante clasificación multietiqueta por descripción de juego.

🚀 **[Prueba la Demo en Vivo aquí](https://game-recommended.alejandrotg.es)**

---

## 📋 Características

- 🔍 **Buscador de Juegos**: Conexión directa con la API pública de Steam para encontrar títulos en español con su respectivo precio y puntuación.
- 🧠 **Análisis de Sentimiento IA**: Clasificación en tiempo real de reseñas en español utilizando un modelo entrenado de Machine Learning (Naive Bayes).
- 🎯 **Recomendación por Descripción (Keras/TensorFlow)**: Red neuronal profunda secuencial (MLP) entrenada en Keras para predecir las probabilidades de géneros y recomendar el TOP 10 de juegos asociados con consulta en paralelo a la API de Steam.
- 📊 **Métricas Comparativas**: Compara el porcentaje de votos positivos registrados oficialmente en Steam contra la clasificación inteligente realizada por nuestro modelo IA.
- 🛡️ **Control de Flujo (Rate Limiting)**: Rate limiter interno integrado por IP para proteger el backend de accesos abusivos y spam.
- 🧪 **Suite de Pruebas**: Cobertura robusta de tests unitarios y de integración con `pytest` y FastAPI `TestClient`.


---

## 📁 Estructura del Proyecto

El repositorio está organizado en los siguientes módulos:

```
backend/            # API REST (FastAPI) y lógica de negocio.
├── app.py          # Configuración principal del servidor y middlewares.
├── middleware.py   # Control de flujo y rate limit por IP.
├── services/       # Módulos de servicios (Steam API y Sentiment Analysis).
├── routers/        # Controladores y definición de rutas.
└── tests/          # Suite de pruebas automatizadas con pytest.
```

---

## 🛠️ Instalación y Configuración

### Requisitos Previos
- Python 3.10 o superior instalado.
- Conda o herramientas de virtualización de Python.

### Configuración del Backend

1. Navega al directorio del backend:
   ```bash
   cd backend
   ```

2. Activa tu entorno de desarrollo (por ejemplo, con Conda):
   ```bash
   conda activate steam-reviews
   ```

3. Instala las dependencias del backend:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta el servidor local de desarrollo:
   ```bash
   uvicorn app:app --reload
   ```
   El servidor estará disponible en [http://localhost:8000](http://localhost:8000). Puedes consultar la documentación interactiva en [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Ejecución de Pruebas

Para garantizar la estabilidad del backend y verificar la modularización del código, ejecuta la suite de pruebas unitarias y de integración:

```bash
# Asegúrate de estar en la carpeta raiz con tu entorno activado
pytest -v
```

Las pruebas cubren:
- **Limpieza de Texto**: Validación del preprocesamiento de comentarios y descripciones en español.
- **Servicio de Steam**: Mockeo completo de las llamadas HTTP de red para evitar peticiones reales.
- **Rutas de API**: Pruebas de integración sobre los endpoints de búsqueda, análisis y recomendación por IA utilizando `TestClient`.
- **Clasificador de Keras**: Pruebas de la lógica de recomendación con inyección de mocks para aislar la carga del modelo TensorFlow.


---

## 🔗 Enlaces de Interés

- **Aplicación en Producción**: [https://game-recommended.alejandrotg.es](https://game-recommended.alejandrotg.es)
- **Documentación de FastAPI (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs) (local)
