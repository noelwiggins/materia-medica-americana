"""
Server-side generation of shareable "remedy card" preview images.
Rendered with Pillow so link previews (Instagram, WhatsApp, iMessage, X, Slack)
show a real branded image instead of nothing — crawlers for those platforms
don't execute JS, so this has to be produced on the server.
"""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

FONT_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts')

INK = (28, 26, 20)
VELLUM = (247, 242, 227)
VELLUM_DARK = (237, 231, 209)
GREEN = (45, 80, 22)
GOLD = (196, 168, 130)
MUTED = (107, 96, 80)
BORDER = (196, 168, 130)

W, H = 1200, 630

_font_cache = {}


def _font(path, size):
    key = (path, size)
    if key not in _font_cache:
        f = ImageFont.truetype(path, size)
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
        _font_cache[key] = f
    return _font_cache[key]


def cinzel(size, weight=600):
    f = ImageFont.truetype(os.path.join(FONT_DIR, 'Cinzel-Variable.ttf'), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def garamond(size, italic=False):
    return ImageFont.truetype(os.path.join(FONT_DIR, 'EBGaramond-Variable.ttf'), size)


def code(size, weight=500):
    f = ImageFont.truetype(os.path.join(FONT_DIR, 'SourceCodePro-Variable.ttf'), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def _wrap(draw, text, font, max_width, max_lines=3):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = f'{cur} {w}'.strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and draw.textlength(cur, font=font) > max_width:
        while draw.textlength(lines[-1] + '…', font=font) > max_width and len(lines[-1]) > 1:
            lines[-1] = lines[-1][:-1]
        lines[-1] += '…'
    return lines


def _texture(base):
    """Subtle paper-grain noise to match the site's vellum texture."""
    noise = Image.effect_noise((W, H), 24).convert('L')
    noise = noise.point(lambda p: 255 - int(p * 0.06))
    base.paste(Image.merge('RGB', (noise, noise, noise)), (0, 0), Image.new('L', (W, H), 12))
    return base


def _base_canvas():
    img = Image.new('RGB', (W, H), VELLUM)
    draw = ImageDraw.Draw(img)
    # double-rule border, manuscript style
    draw.rectangle([28, 28, W - 28, H - 28], outline=GOLD, width=2)
    draw.rectangle([38, 38, W - 38, H - 38], outline=BORDER, width=1)
    return img, draw


def _eyebrow(draw, text, y=68):
    f = code(22, 500)
    draw.text((64, y), text.upper(), font=f, fill=MUTED)


def _tradition_badges(draw, x, y, traditions):
    """Small colored dots + labels for each tradition represented."""
    cx = x
    f = code(20, 500)
    for t in traditions[:6]:
        color = t.get('color', '#2D5016')
        color = tuple(int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) if isinstance(color, str) else color
        draw.ellipse([cx, y + 4, cx + 14, y + 18], fill=color)
        label = t.get('name', '').split(' ')[0]
        draw.text((cx + 20, y), label, font=f, fill=MUTED)
        cx += 20 + draw.textlength(label, font=f) + 26
    return cx


def render_plant_card(plant, traditions_by_id):
    img, draw = _base_canvas()
    _eyebrow(draw, 'Materia Medica Americana · 18 Traditions · 4,000 Years')

    # tradition badges
    trads = [traditions_by_id.get(tid, {'name': tid, 'color': '#6B6050'}) for tid in plant.get('traditions', [])]
    _tradition_badges(draw, 64, 108, trads)

    # plant common name (large, Cinzel)
    name = plant.get('common_name', 'Untitled Remedy')
    name_font = cinzel(64, 700)
    name_lines = _wrap(draw, name, name_font, W - 128, max_lines=2)
    y = 175
    for line in name_lines:
        draw.text((64, y), line, font=name_font, fill=INK)
        y += 74

    # botanical name (italic-ish garamond, green)
    botanical = plant.get('modern_botanical', '')
    if botanical:
        bf = code(26, 400)
        draw.text((64, y + 4), botanical, font=bf, fill=GREEN)
        y += 46

    y += 20
    draw.line([64, y, W - 64, y], fill=BORDER, width=1)
    y += 28

    # plain summary — condition treated + preparation
    entries = list(plant.get('entries', {}).values())
    first = entries[0] if entries else {}
    condition = first.get('condition', '')
    summary_font = garamond(32)
    if condition:
        lines = _wrap(draw, f'Traditionally used for: {condition}', summary_font, W - 128, max_lines=2)
        for line in lines:
            draw.text((64, y), line, font=summary_font, fill=INK)
            y += 42

    # modern research validation badge
    mr = plant.get('modern_research')
    if mr and mr.get('status') in ('fully_validated', 'breakthrough_validated', 'validated_essential_medicine'):
        y += 14
        badge_text = f"✓ Modern validation — {mr.get('key_compound', '')}"
        bf = code(24, 600)
        tw = draw.textlength(badge_text, font=bf)
        draw.rounded_rectangle([64, y, 64 + tw + 32, y + 44], radius=4, fill=(232, 240, 224))
        draw.text((80, y + 10), badge_text, font=bf, fill=GREEN)
        y += 60

    # convergence score, bottom right
    conv = plant.get('convergence_score', 0)
    cf = cinzel(40, 700)
    conv_text = str(conv)
    conv_w = draw.textlength(conv_text, font=cf)
    draw.text((W - 100 - conv_w, H - 130), conv_text, font=cf, fill=GREEN)
    lf = code(18, 500)
    draw.text((W - 130 - conv_w, H - 82), 'TRADITIONS\nAGREE', font=lf, fill=MUTED, align='right')

    # footer
    draw.line([64, H - 70, W - 64, H - 70], fill=BORDER, width=1)
    ff = code(20, 500)
    draw.text((64, H - 54), 'medica-americana.up.railway.app', font=ff, fill=MUTED)

    return _texture(img)


def render_search_card(query, snippet, tradition_count, plant_name=None):
    img, draw = _base_canvas()
    _eyebrow(draw, 'Materia Medica Americana · Archive Search')

    label_f = code(22, 500)
    draw.text((64, 110), '✦ ARCHIVE INTELLIGENCE · CROSS-TRADITION SUMMARY', font=label_f, fill=GREEN)

    q_font = cinzel(52, 700)
    q_display = f'"{query}"'
    q_lines = _wrap(draw, q_display, q_font, W - 128, max_lines=2)
    y = 165
    for line in q_lines:
        draw.text((64, y), line, font=q_font, fill=INK)
        y += 62

    y += 16
    draw.line([64, y, W - 64, y], fill=BORDER, width=1)
    y += 30

    if snippet:
        sf = garamond(30)
        lines = _wrap(draw, snippet, sf, W - 128, max_lines=5)
        for line in lines:
            draw.text((64, y), line, font=sf, fill=INK)
            y += 40

    # stat strip
    y = H - 150
    draw.line([64, y, W - 64, y], fill=BORDER, width=1)
    y += 24
    sf = code(24, 600)
    stat_text = f'{tradition_count} tradition{"s" if tradition_count != 1 else ""} referenced'
    draw.text((64, y), stat_text, font=sf, fill=GREEN)
    if plant_name:
        pf = code(22, 500)
        draw.text((64, y + 36), f'Top remedy: {plant_name}', font=pf, fill=MUTED)

    ff = code(20, 500)
    draw.text((64, H - 54), 'medica-americana.up.railway.app', font=ff, fill=MUTED)

    return _texture(img)


def to_png_bytes(img):
    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf
