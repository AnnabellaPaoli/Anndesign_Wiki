import json
import sys
import io
import os
import zipfile
from generate_slides import generate_slide, BRAND
from generate_content_gemini import generate_content
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 1. IDENTIDAD DE MARCA
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",  # Linux
        "C:/Windows/Fonts/times.ttf",                                        # Windows
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",           # Mac
    ],
    "italic": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "C:/Windows/Fonts/timesi.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ],
}


def _resolve_fonts():
    resolved = {}
    missing = []
    for style, candidates in _FONT_CANDIDATES.items():
        found = next((p for p in candidates if os.path.isfile(p)), None)
        if found is None:
            missing.append(style)
        resolved[style] = found
    if missing:
        print("No se encontró ninguna fuente instalada para:", ", ".join(missing))
        sys.exit(1)
    return resolved


BRAND = {
    "colors": {
        "ivory": "#FBF8F3",
        "ink": "#1B1512",
        "ink_soft": "#55493d",
        "gold": "#B4903F",
        "gold_deep": "#8C6A2F",
        "rose_line": "#E3BEC5",
    },
    "fonts": _resolve_fonts(),
    "wordmark": {"regular": "Ann", "accent": "Design"},
}

W = H = 1080

# ---------------------------------------------------------------------------
# 2. UTILIDADES DE DIBUJO
# ---------------------------------------------------------------------------

def _font(brand, style, size):
    return ImageFont.truetype(brand["fonts"][style], size)


def _canvas(brand):
    return Image.new("RGB", (W, H), brand["colors"]["ivory"])


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _centered(draw, text, font, y, fill, max_width=820, line_gap=14):
    for line in _wrap(draw, text, font, max_width):
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def _hairline(draw, y, brand, width=160):
    color = brand["colors"]["gold"]
    draw.line([(W - width) / 2, y, (W + width) / 2, y], fill=color, width=1)


def _ornament(draw, cx, cy, brand, r=18):
    color = brand["colors"]["gold"]
    draw.line([cx, cy - r - 8, cx, cy + r + 8], fill=color, width=1)
    draw.line([cx - r - 8, cy, cx + r + 8, cy], fill=color, width=1)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=1)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=color)


def _footer_brand(draw, brand):
    f_reg = _font(brand, "regular", 26)
    f_ita = _font(brand, "italic", 26)
    y = H - 90
    ann = brand["wordmark"]["regular"]
    design = brand["wordmark"]["accent"]
    ann_w = draw.textlength(ann, font=f_reg)
    des_w = draw.textlength(design, font=f_ita)
    x0 = (W - ann_w - des_w) / 2
    draw.text((x0, y), ann, font=f_reg, fill=brand["colors"]["ink"])
    draw.text((x0 + ann_w, y), design, font=f_ita, fill=brand["colors"]["gold_deep"])


def _icon(draw, kind, cx, cy, brand, s=1.0):
    color = brand["colors"]["gold_deep"]
    if kind == "chat":
        w, h = 90 * s, 64 * s
        x0, y0 = cx - w / 2, cy - h / 2
        draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=14 * s, outline=color, width=3)
        draw.polygon([(x0 + 22 * s, y0 + h), (x0 + 22 * s, y0 + h + 16 * s), (x0 + 40 * s, y0 + h)], fill=color)
        for i in range(3):
            dx = x0 + w / 2 - 18 * s + i * 18 * s
            draw.ellipse([dx - 3.5 * s, cy - 3.5 * s, dx + 3.5 * s, cy + 3.5 * s], fill=color)
    elif kind == "browser":
        w, h = 96 * s, 68 * s
        x0, y0 = cx - w / 2, cy - h / 2
        draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8 * s, outline=color, width=3)
        draw.line([x0, y0 + 18 * s, x0 + w, y0 + 18 * s], fill=color, width=2)
        for i in range(3):
            dx = x0 + 12 * s + i * 14 * s
            draw.ellipse([dx - 2.5 * s, y0 + 9 * s - 2.5 * s, dx + 2.5 * s, y0 + 9 * s + 2.5 * s], fill=color)
        draw.line([x0 + 16 * s, y0 + 40 * s, x0 + w - 16 * s, y0 + 40 * s], fill=color, width=2)
        draw.line([x0 + 16 * s, y0 + 52 * s, x0 + w - 36 * s, y0 + 52 * s], fill=color, width=2)
    elif kind == "stack":
        w = 84 * s
        for dy in (-22, 0, 22):
            y = cy + dy * s
            draw.ellipse([cx - w / 2, y - 10 * s, cx + w / 2, y + 10 * s], outline=color, width=3)
    elif kind == "check":
        r = 26 * s
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
        draw.line([cx - 10 * s, cy, cx - 2 * s, cy + 9 * s], fill=color, width=3)
        draw.line([cx - 2 * s, cy + 9 * s, cx + 12 * s, cy - 8 * s], fill=color, width=3)
    elif kind == "mail":
        w, h = 90 * s, 58 * s
        x0, y0 = cx - w / 2, cy - h / 2
        draw.rectangle([x0, y0, x0 + w, y0 + h], outline=color, width=3)
        draw.line([x0, y0, cx, cy + 6 * s], fill=color, width=3)
        draw.line([x0 + w, y0, cx, cy + 6 * s], fill=color, width=3)


# ---------------------------------------------------------------------------
# 3. RENDERIZADORES
# ---------------------------------------------------------------------------

def render_portada(cfg, brand):
    c = _canvas(brand)
    d = ImageDraw.Draw(c)
    colors = brand["colors"]
    _ornament(d, W // 2, 280, brand)
    f_h1 = _font(brand, "regular", 52)
    f_h1i = _font(brand, "italic", 52)
    ann, design = brand["wordmark"]["regular"], brand["wordmark"]["accent"]
    ann_w = d.textlength(ann, font=f_h1)
    x0 = (W - ann_w - d.textlength(design, font=f_h1i)) / 2
    d.text((x0, 400), ann, font=f_h1, fill=colors["ink"])
    d.text((x0 + ann_w, 400), design, font=f_h1i, fill=colors["gold_deep"])
    _hairline(d, 455, brand)
    _centered(d, cfg.get("text", ""), _font(brand, "italic", 28), 500, colors["ink_soft"], max_width=760)
    _footer_brand(d, brand)
    return c


def render_servicio(cfg, brand):
    c = _canvas(brand)
    d = ImageDraw.Draw(c)
    colors = brand["colors"]
    _icon(d, cfg.get("icon", "chat"), W // 2, 250, brand)
    _centered(d, cfg.get("title", ""), _font(brand, "regular", 40), 340, colors["ink"], max_width=760)
    _hairline(d, 410, brand)
    _centered(d, cfg.get("desc", ""), _font(brand, "regular", 30), 460, colors["ink_soft"], max_width=720)
    _footer_brand(d, brand)
    return c


def render_proceso(cfg, brand):
    c = _canvas(brand)
    d = ImageDraw.Draw(c)
    colors = brand["colors"]
    _centered(d, cfg.get("title", "Cómo funciona"), _font(brand, "regular", 40), 100, colors["ink"])
    _hairline(d, 150, brand)
    
    steps = cfg.get("steps", [])[:4]
    f_title = _font(brand, "regular", 30)
    f_desc = _font(brand, "italic", 26)
    f_num = _font(brand, "italic", 30)
    
    line_x, r, start_y, gap = 150, 30, 260, 160
    for i, step in enumerate(steps):
        cy = start_y + i * gap
        d.ellipse([line_x - r, cy - r, line_x + r, cy + r], outline=colors["gold_deep"], width=2)
        num = str(i + 1)
        nw = d.textlength(num, font=f_num)
        d.text((line_x - nw / 2, cy - f_num.size / 2 - 4), num, font=f_num, fill=colors["gold"])
        d.text((line_x + 60, cy - 25), step.get("title", ""), font=f_title, fill=colors["ink"])
        d.text((line_x + 60, cy + 10), step.get("desc", ""), font=f_desc, fill=colors["ink_soft"])
        
    _footer_brand(d, brand)
    return c


def render_faq(cfg, brand):
    c = _canvas(brand)
    d = ImageDraw.Draw(c)
    colors = brand["colors"]
    _centered(d, cfg.get("title", "Preguntas Frecuentes"), _font(brand, "regular", 42), 140, colors["ink"])
    _hairline(d, 200, brand)
    _centered(d, "Q: " + cfg.get("q", ""), _font(brand, "bold", 32), 280, colors["gold_deep"], max_width=760)
    _centered(d, cfg.get("a", ""), _font(brand, "regular", 28), 420, colors["ink_soft"], max_width=760)
    _footer_brand(d, brand)
    return c


def render_cierre(cfg, brand):
    c = _canvas(brand)
    d = ImageDraw.Draw(c)
    colors = brand["colors"]
    _ornament(d, W // 2, 280, brand)
    _centered(d, cfg.get("title", "Let's Work Together"), _font(brand, "regular", 46), 400, colors["ink"])
    _hairline(d, 465, brand)
    _centered(d, cfg.get("cta", "Envíanos un mensaje"), _font(brand, "italic", 30), 520, colors["gold_deep"])
    _footer_brand(d, brand)
    return c

# ---------------------------------------------------------------------------
# 4. COMPATIBILIDAD CON WIKI (MÉTODO HISTÓRICO DE CONFIGURACIÓN)
# ---------------------------------------------------------------------------
def generate_slide(objeto_datos, ruta_salida):
    """
    Función puente ejecutada por el pipeline multipáginas del main.py.
    No requiere cambios estructurales en tu flujo.
    """
    pass
