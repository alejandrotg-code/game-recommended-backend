import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def build_linkedin_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    
    # Colores de marca
    PRIMARY = colors.HexColor("#1e1b4b")       # Indigo muy oscuro
    SECONDARY = colors.HexColor("#6d28d9")     # Violeta vibrante
    ACCENT = colors.HexColor("#059669")        # Verde esmeralda (Novedad)
    TEXT_DARK = colors.HexColor("#1f2937")     # Gris oscuro para texto
    TEXT_MUTED = colors.HexColor("#4b5563")    # Gris secundario
    BG_LIGHT = colors.HexColor("#f8fafc")      # Fondo tarjetas
    BORDER_COLOR = colors.HexColor("#e2e8f0")

    # Estilos de párrafo
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=SECONDARY,
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=TEXT_DARK
    )

    post_box_style = ParagraphStyle(
        'PostBoxText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#0f172a")
    )

    bold_label_style = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=PRIMARY
    )

    story = []

    # Header / Título
    story.append(Paragraph("Estrategia LinkedIn: Lanzamiento \"Recomendador por IA\"", title_style))
    story.append(Paragraph("<b>Proyecto:</b> Game Recommended (Steam Reviews Recommender) &nbsp;|&nbsp; <b>Zona Horaria:</b> Canarias (WEST / UTC+1) &nbsp;|&nbsp; <b>Fecha:</b> Agosto 2026", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SECONDARY, spaceAfter=15))

    # SECCIÓN 1: NOVEDADES DEL PROYECTO
    story.append(Paragraph("1. Resumen de Novedades del Proyecto", h1_style))
    
    features_html = """
    • <b>Selección Flexible de Recomendaciones:</b> El usuario puede elegir cuántos juegos solicitar a la IA (4, 10 o 20 títulos).<br/>
    • <b>Paginación Dinámica en Frontend:</b> Paginación fluida (4 juegos por página) con controles de navegación (&lt; Anterior, Siguiente &gt;, contador de página) que evita el scroll infinito en listas largas.<br/>
    • <b>Pipeline Híbrido RAG (Groq LLM + Steam Search API):</b> Integración que combina la comprensión en lenguaje natural con la recolección en tiempo real.<br/>
    • <b>Enriquecimiento con Referentes de la Industria (Benchmark Games):</b> Groq extrae grandes clásicos del género (ej. <i>Stardew Valley</i>, <i>Slime Rancher</i>, <i>Farm Together</i>) y consulta sus datos oficiales en vivo en Steam, garantizando que los mejores títulos siempre aparezcan junto a las novedades.<br/>
    • <b>Actualización de UI/UX:</b> Badge "NOVEDAD" en verde esmeralda y renovada interfaz responsiva en el header y contenedor principal.
    """
    story.append(Paragraph(features_html, body_style))
    story.append(Spacer(1, 10))

    # SECCIÓN 2: MEJORES HORAS Y DÍAS EN CANARIAS
    story.append(Paragraph("2. Mejores Días y Horas para Publicar en LinkedIn (Desde Canarias)", h1_style))
    
    timing_data = [
        [
            Paragraph("<b>Días Top (Máximo Alcance)</b>", bold_label_style),
            Paragraph("<b>Martes, Miércoles y Jueves</b> (Días de mayor engagement orgánico en LinkedIn a nivel España y LatAm).", body_style)
        ],
        [
            Paragraph("<b>Franja Mañana (Canarias)</b>", bold_label_style),
            Paragraph("<b>07:30 - 08:30 WEST</b> (Coincide con 08:30 - 09:30 en Península / Europa central). Ideal para profesionales en su café inicial.", body_style)
        ],
        [
            Paragraph("<b>Franja Mediodía ⭐ (MEJOR)</b>", bold_label_style),
            Paragraph("<b>11:30 - 13:00 WEST</b> (Coincide con 12:30 - 14:00 Península). Pico máximo de actividad previa a la pausa de comida.", body_style)
        ],
        [
            Paragraph("<b>Franja Tarde</b>", bold_label_style),
            Paragraph("<b>16:30 - 17:30 WEST</b> (Coincide con 17:30 - 18:30 Península). Cierre de jornada laboral.", body_style)
        ],
        [
            Paragraph("<b>Días a Evitar</b>", bold_label_style),
            Paragraph("Viernes tarde, Sábados y Domingos (El alcance profesional cae más de un 60%).", body_style)
        ]
    ]

    timing_table = Table(timing_data, colWidths=[4.5*cm, 12.5*cm])
    timing_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(timing_table)
    story.append(Spacer(1, 15))

    # SECCIÓN 3: PROPUESTAS DE POSTS
    story.append(Paragraph("3. Propuestas de Post para LinkedIn", h1_style))

    def make_post_card(title, tag, text_content):
        card_data = [
            [Paragraph(f"<b>{title}</b> &nbsp;&nbsp;<font color='#059669'>[{tag}]</font>", bold_label_style)],
            [Paragraph(text_content.replace('\n', '<br/>'), post_box_style)]
        ]
        t = Table(card_data, colWidths=[17*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
            ('LINEBELOW', (0,0), (-1,0), 1, SECONDARY),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    # POST 1: ENFOQUE TÉCNICO
    post1_text = """🚀 ¿Cómo combinar la potencia de un LLM con la API de Steam en tiempo real para recomendar videojuegos por estado de ánimo?

En el proyecto Game Recommended acabamos de lanzar una de las actualizaciones más potentes hasta la fecha para el "Recomendador por IA" 🤖🎮

💡 El reto técnico:
Cuando un usuario busca "un juego relajante para tener mi granja y plantar hortalizas", los motores de búsqueda por coincidencias de texto exacto suelen fallar o devolver títulos oscuros porque clasicazos como Stardew Valley no contienen la frase literal "farming simulation" en su nombre.

⚙️ La solución (Pipeline Híbrido RAG + Benchmark Enrichment):
1️⃣ Groq (Llama 3) analiza la intención y extrae tanto palabras clave de búsqueda como una lista de referentes clave de la industria para ese género (ej. Stardew Valley, Slime Rancher, Farm Together).
2️⃣ El backend en FastAPI realiza peticiones concurrentes a la API oficial de Steam para obtener datos en vivo (precios reales en €, portadas y metascores) tanto de los referentes como de las novedades.
3️⃣ Groq evalúa el pool enriquecido, selecciona las mejores opciones y genera razones personalizadas en español ("✨ Por qué encaja contigo").

Además, en el frontend (React + Tailwind CSS) hemos añadido:
✅ Selector dinámico de cantidad de recomendaciones (4, 10 o 20 juegos).
✅ Paginación fluida de 4 en 4 para evitar el scroll infinito y mejorar la UX.

💻 Stack: Python, FastAPI, LangChain, Groq LLM, React, Vite, Tailwind CSS.

👇 ¿Qué os parece este enfoque para evitar el sesgo de los buscadores tradicionales? Dejo el código en los comentarios.

#Python #FastAPI #ReactJS #AI #LLM #Groq #WebDevelopment #SoftwareEngineering #Steam"""

    story.append(make_post_card("OPCIÓN 1: Enfoque Técnico & Arquitectura RAG", "Ideal para Desarrolladores & Tech Community", post1_text))
    story.append(Spacer(1, 12))

    # POST 2: ENFOQUE PRODUCTO Y UX
    post2_text = """🎮 ¡Nueva funcionalidad en Game Recommended! Encuentra tu próximo juego según tu estado de ánimo con IA 🌾🚀

A todos nos ha pasado: llegas a casa cansado, quieres jugar a algo específico (ej. "un RPG corto de puzles con buena música para desconectar"), pero pasas 45 minutos buscando en catálogos sin saber qué elegir.

Para resolver esto, hemos evolucionado el Recomendador por IA:

✨ ¿Qué hay de nuevo?
• 🎯 Elige cuántos juegos quieres: 4, 10 o 20 recomendaciones personalizadas.
• 📄 Paginación cómoda: Explora los resultados página a página sin perderte en listas infinitas.
• 🏆 Éxitos reconocidos + Novedades: La IA asegura que siempre aparezcan grandes referentes (como Stardew Valley o Slime Rancher) junto con descubrimientos recientes.
• ⚡ Precios y tiendas en tiempo real: Enlaces directos a Steam, Instant Gaming y G2A con precios actualizados.

Diseñado con una interfaz oscura futurista para una navegación ultra rápida ⚡

🔗 Pruébalo directamente en la web (enlace en comentarios) y dime qué te recomienda hoy.

#ProductDesign #UIUX #React #AI #GamingCommunity #IndieGames #WebDev"""

    story.append(KeepTogether([
        make_post_card("OPCIÓN 2: Enfoque Producto, UX & Showcase", "Ideal para Reclutadores & Product Managers", post2_text),
        Spacer(1, 12)
    ]))

    # POST 3: ENFOQUE PROBLEM SOLVING & LECCIONES APRENDIDAS
    post3_text = """❓ "¿Por qué la IA me recomendaba juegos desconocidos cuando le pedía un juego de granja relajante?"

Durante las pruebas de Game Recommended nos encontramos con un problema curioso de los sistemas RAG tradicionales:

Al convertir la búsqueda del usuario a palabras clave en inglés para la API de Steam ("farming simulation"), el buscador de Steam devolvía juegos cuyo título contenía literalmente esa frase (ej. "Aquaculture Land: Fish Farming Simulation"). ¡Pero dejaba fuera a Stardew Valley porque se llama simplemente "Stardew Valley"! 🤦‍♂️

Moraleja: La búsqueda semántica y las APIs externas deben complementarse.

🛠️ La lección aprendida:
Diseñamos un pipeline de enriquecimiento previo. Ahora la IA no solo traduce palabras clave, sino que identifica automáticamente los videojuegos referentes del género y consulta sus datos oficiales en vivo.

El resultado: Una recomendación equilibrada entre clásicos imprescindibles y joyas ocultas de Steam, con soporte para hasta 20 juegos y paginación en React 🚀

¿Habéis tenido problemas similares conectando LLMs con APIs de terceros? Me encantará leer vuestras experiencias 👇

#SoftwareDevelopment #PromptEngineering #ArtificialIntelligence #Python #React #BuildInPublic"""

    story.append(KeepTogether([
        make_post_card("OPCIÓN 3: Enfoque Problem-Solving & Storytelling", "Ideal para Generar Conversación & Engagement", post3_text)
    ]))

    doc.build(story)
    print(f"PDF generado con éxito en: {filename}")

if __name__ == '__main__':
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "LinkedIn_Posts_Game_Recommended.pdf")
    build_linkedin_pdf(desktop_path)
