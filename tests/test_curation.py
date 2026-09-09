from services.curation import is_spam_or_low_substance, calculate_substance_score, curate_diverse_reviews


def test_is_spam_or_low_substance():
    assert is_spam_or_low_substance("") is True
    assert is_spam_or_low_substance("   ") is True
    assert is_spam_or_low_substance("hola") is True
    assert is_spam_or_low_substance("░▒▓█░▒▓█ gatazo ░▒▓█") is True
    assert is_spam_or_low_substance("aaaaaaaaaaaaaaa") is True

    valid_text = "Este videojuego tiene un sistema de combate increíble y gran rendimiento."
    assert is_spam_or_low_substance(valid_text) is False


def test_calculate_substance_score():
    score_short = calculate_substance_score("juego regular", 60)
    score_rich = calculate_substance_score(
        "Excelente ambientación sonora, mecánicas variadas de sigilo y una historia apasionante.", 1200
    )
    assert score_rich > score_short


def test_curate_diverse_reviews():
    raw_reviews = [
        {"review": "░▒▓█ spam meme ░▒▓█", "author": {"playtime_forever": 10}},
        {"review": "malo", "author": {"playtime_forever": 5}},
        {"review": "La historia principal es fascinante con giros argumentales sorprendentes.", "author": {"playtime_forever": 600}},
        {"review": "El rendimiento gráfico cae en zonas boscosas con tarjetas de gama media.", "author": {"playtime_forever": 1200}},
        {"review": "La música y la banda sonora ambiental son de primer nivel.", "author": {"playtime_forever": 300}},
    ]

    curated = curate_diverse_reviews(raw_reviews, None, target_limit=2)
    assert len(curated) == 2
    # Comprobar que no incluye el spam
    for r in curated:
        assert "spam" not in r["review"]
