from services import sentiment_service

def test_limpiar_resena():
    """
    Verifica que el método de limpieza elimine correctamente menciones,
    hashtags, signos de puntuación, números, convierta a minúsculas y recorte espacios.
    """
    test_cases = [
        ("¡HOLA MUNDO!", "hola mundo"),
        ("Este es un @usuario de prueba", "este es un  de prueba"),
        ("Me encanta este juego #recomendado", "me encanta este juego recomendado"),
        ("El precio es de 50 dolares", "el precio es de  dolares"),
        ("   Espacios en los extremos   ", "espacios en los extremos"),
        ("¡¡Wow!! Increíble... 10/10.", "wow increíble"),
    ]
    
    for entrada, esperado in test_cases:
        resultado = sentiment_service.limpiar_resena(entrada)
        assert resultado == esperado, f"Fallo para '{entrada}'. Esperado: '{esperado}', Obtenido: '{resultado}'"

def test_predecir_sentimientos():
    """
    Verifica el comportamiento de predicción en lote usando el modelo mockeado en conftest.py.
    """
    textos = [
        "Este juego es muy bueno y excelente",
        "No me gustó para nada, es aburrido",
        "¡Un juegazo total, super divertido!",
        "Una basura completa de juego"
    ]
    # Esperado según el mock configurado en conftest.py:
    # 1. contiene "bueno" / "excelente" -> 1 (Positivo)
    # 2. "aburrido" -> 0 (Negativo)
    # 3. contiene "juegazo" / "divertido" -> 1 (Positivo)
    # 4. "basura" -> 0 (Negativo)
    esperado = [1, 0, 1, 0]
    
    resultado = sentiment_service.predecir_sentimientos(textos)
    assert resultado == esperado, f"Esperado {esperado}, pero se obtuvo {resultado}"
