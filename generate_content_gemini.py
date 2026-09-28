from dotenv import load_dotenv
import sys
import os
import json
from google import genai
from google.genai import types

load_dotenvd()
MODEL_NAME = "gemini-3.5-flash"  # cámbialo aquí si Google lo renombra

# ---------------------------------------------------------------------------
# El "manual de estilo" que la IA debe seguir. Edítalo si tu tono cambia.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Eres quien escribe el contenido de Instagram para AnnDesign,
un estudio de automatización con IA, diseño web e infraestructura digital.

Tono de marca: elegante, cálido, directo. Frases cortas. Nunca uses signos
de exclamación de más ni lenguaje de venta agresivo ("¡compra ya!"). Habla
como una persona que sabe lo que hace y no necesita gritarlo.

Tu tarea: recibir un tema general y devolver un arreglo JSON de slides para
un carrusel de Instagram, usando SOLO estos tipos de slide y estos campos
exactos (no inventes campos nuevos, no cambies los nombres de las claves):

1. "portada" — { "type": "portada", "name": "slideN-portada", "text": "..." }
   Una frase de una o dos líneas presentando el tema del carrusel.

2. "servicio" — { "type": "servicio", "name": "...", "icon": "chat"|"browser"|"stack", "title": "...", "desc": "..." }
   Usa "chat" para automatización/WhatsApp, "browser" para web/landing,
   "stack" para infraestructura/datos.

3. "proceso" — { "type": "proceso", "name": "...", "title": "...", "steps": [{"title": "...", "desc": "..."}, ...] }
   Máximo 4 pasos.

4. "faq" — { "type": "faq", "name": "...", "title": "...", "items": [{"q": "...", "a": "..."}, ...] }
   Máximo 2 preguntas.

5. "cierre" — { "type": "cierre", "name": "...", "title": "...", "desc": "...", "link": "studioanndesign.com" }
   Siempre el último slide.

Reglas:
- Entre 5 y 7 slides en total.
- El primer slide siempre es "portada" y el último siempre "cierre".
- Los textos deben ser específicos al tema que te den, no genéricos.
- Responde ÚNICAMENTE con el JSON del arreglo, sin explicación antes o después,
  sin usar bloques de código con ```.
"""


def generate_content(topic: str) -> list:
    #api_key = os.environ.get("GEMINI_API_KEY")
    GEMINI_API_KEY=os.environ.get(GEMINI_API_KEY)
    api_key =GEMINI_API_KEY
    if not api_key:
        print("No encontré la variable de entorno GEMINI_API_KEY.")
        print("Revisa las instrucciones al inicio de este archivo.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"Tema del carrusel: {topic}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    raw_text = response.text.strip()

    # Por si el modelo igual envuelve la respuesta en ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


def main():
    if len(sys.argv) < 2:
        print('Uso: python generate_content_gemini.py "tu tema en una frase"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"Generando contenido para: {topic!r} (usando {MODEL_NAME}) ...")

    slides = generate_content(topic)

    out_path = "content.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)

    print(f"✓ {out_path} creado con {len(slides)} slides.")
    print("Ahora corre: python generate_slides.py content.json")


if __name__ == "__main__":
    main()
