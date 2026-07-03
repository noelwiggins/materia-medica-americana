from flask import Flask, send_from_directory, jsonify, Response, abort, request
import os
import json
import base64
import functools
import html as html_lib

import og_image

app = Flask(__name__, static_folder='static')

# ── Data loading (cached) ────────────────────────────────────────────────
@functools.lru_cache(maxsize=1)
def load_plants():
    with open('static/data/plants.json', encoding='utf-8') as f:
        return json.load(f)['plants']

@functools.lru_cache(maxsize=1)
def load_traditions():
    with open('static/data/traditions.json', encoding='utf-8') as f:
        data = json.load(f)
        trads = data.get('traditions', data if isinstance(data, list) else [])
        return {t['id']: t for t in trads}

def find_plant(plant_id):
    for p in load_plants():
        if p.get('id') == plant_id:
            return p
    return None

# ── Base64url helpers for stateless search-share payloads ───────────────
def encode_payload(d):
    raw = json.dumps(d, separators=(',', ':')).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')

def decode_payload(s):
    pad = '=' * (-len(s) % 4)
    raw = base64.urlsafe_b64decode(s + pad)
    return json.loads(raw.decode('utf-8'))


# ── Core static app ───────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory('static/data', filename)


# ── Share landing pages (server-rendered so link-preview crawlers see OG tags) ──
SHARE_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">

<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{image_url}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{page_url}">
<meta property="og:site_name" content="Materia Medica Americana">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image_url}">

<meta http-equiv="refresh" content="0; url={redirect_url}">
<style>
  body {{ font-family: Georgia, serif; background:#F7F2E3; color:#1C1A14; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
  a {{ color:#2D5016; }}
</style>
</head>
<body>
  <p>Loading Materia Medica Americana… <a href="{redirect_url}">Continue</a></p>
  <script>window.location.replace({redirect_url_js});</script>
</body>
</html>"""


@app.route('/share/p/<plant_id>')
def share_plant(plant_id):
    plant = find_plant(plant_id)
    if not plant:
        abort(404)

    entries = list(plant.get('entries', {}).values())
    condition = entries[0].get('condition', '') if entries else ''
    title = f"{plant.get('common_name', 'A Remedy')} — Materia Medica Americana"
    description = (
        f"Traditionally used for {condition}. " if condition else ""
    ) + f"Documented across {len(plant.get('traditions', []))} tradition(s), spanning up to 4,000 years of recorded use."
    description = description.strip()[:300]

    page_url = request.url
    image_url = f"{request.url_root.rstrip('/')}/api/og/plant/{plant_id}.png"
    redirect_url = f"{request.url_root.rstrip('/')}?plant={plant_id}"

    return Response(SHARE_PAGE_TEMPLATE.format(
        title=html_lib.escape(title),
        description=html_lib.escape(description),
        image_url=image_url,
        page_url=page_url,
        redirect_url=redirect_url,
        redirect_url_js=json.dumps(redirect_url),
    ), mimetype='text/html')


@app.route('/share/s/<payload>')
def share_search(payload):
    try:
        data = decode_payload(payload)
    except Exception:
        abort(404)

    query = data.get('q', 'a remedy')
    snippet = data.get('s', '')
    title = f'"{query}" — Materia Medica Americana'
    description = snippet[:300] if snippet else f'Cross-tradition findings on {query} from an archive of 18 world medical traditions spanning 4,000 years.'

    page_url = request.url
    image_url = f"{request.url_root.rstrip('/')}/api/og/search/{payload}.png"
    redirect_url = f"{request.url_root.rstrip('/')}?q={base64.urlsafe_b64encode(query.encode()).decode()}"

    return Response(SHARE_PAGE_TEMPLATE.format(
        title=html_lib.escape(title),
        description=html_lib.escape(description),
        image_url=image_url,
        page_url=page_url,
        redirect_url=redirect_url,
        redirect_url_js=json.dumps(redirect_url),
    ), mimetype='text/html')


# ── OG image generation (PNG, cached in-process) ─────────────────────────
@functools.lru_cache(maxsize=256)
def _plant_card_bytes(plant_id):
    plant = find_plant(plant_id)
    if not plant:
        return None
    img = og_image.render_plant_card(plant, load_traditions())
    return og_image.to_png_bytes(img).getvalue()

@app.route('/api/og/plant/<plant_id>.png')
def og_plant(plant_id):
    data = _plant_card_bytes(plant_id)
    if data is None:
        abort(404)
    return Response(data, mimetype='image/png', headers={'Cache-Control': 'public, max-age=86400'})


@functools.lru_cache(maxsize=256)
def _search_card_bytes(payload):
    try:
        data = decode_payload(payload)
    except Exception:
        return None
    img = og_image.render_search_card(
        query=data.get('q', ''),
        snippet=data.get('s', ''),
        tradition_count=data.get('c', 0),
        plant_name=data.get('n'),
    )
    return og_image.to_png_bytes(img).getvalue()

@app.route('/api/og/search/<payload>.png')
def og_search(payload):
    data = _search_card_bytes(payload)
    if data is None:
        abort(404)
    return Response(data, mimetype='image/png', headers={'Cache-Control': 'public, max-age=86400'})


# ── Catch-all static/file serving (kept last, matches original behavior) ──
@app.route('/<path:filename>')
def serve_file(filename):
    if filename.startswith('static/'):
        return send_from_directory('.', filename)
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
