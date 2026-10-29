from flask import Flask, send_from_directory, jsonify, Response, abort, request
import os
import json
import base64
import functools
import html as html_lib

import og_image

# ── R2 reader-data redirect ───────────────────────────────────────────────────
_R2_BASE = os.environ.get("R2_BASE_URL", "").rstrip("/")


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
_MOBILE_UA = ('iphone', 'ipod', 'android', 'mobile', 'blackberry', 'opera mini', 'iemobile')


def _is_phone():
    ua = (request.headers.get('User-Agent') or '').lower()
    return any(k in ua for k in _MOBILE_UA) and 'ipad' not in ua


@app.route('/')
def index():
    # Phones get the mobile app unless they chose the full site ("Full site" sets pc_view=full)
    if request.args.get('view') == 'full':
        resp = send_from_directory('.', 'index.html')
        resp.set_cookie('pc_view', 'full', max_age=60 * 60 * 24 * 180)
        return resp
    if request.cookies.get('pc_view') != 'full' and _is_phone():
        return send_from_directory('static/m', 'index.html')
    return send_from_directory('.', 'index.html')


@app.route('/m')
@app.route('/m/')
def mobile_app():
    resp = send_from_directory('static/m', 'index.html')
    resp.set_cookie('pc_view', '', max_age=0)
    return resp

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory('static/data', filename)

@app.route('/reader-data/<path:filename>')
def serve_reader_data(filename):
    if _R2_BASE:
        from flask import redirect
        return redirect(f"{_R2_BASE}/reader-data/{filename}", code=301)
    return send_from_directory('static/reader-data', filename)


# ── Manuscript page search (translations copied from Oedio) ──────────────
@functools.lru_cache(maxsize=1)
def load_page_index():
    """Every reader-data page that carries an English translation: (file, index, label, hay, text, translation)."""
    import glob
    idx = []
    for path in sorted(glob.glob('static/reader-data/*.json')):
        name = os.path.basename(path)
        try:
            with open(path, encoding='utf-8') as f:
                pages = json.load(f)
        except Exception:
            continue
        if not isinstance(pages, list):
            continue
        for i, p in enumerate(pages):
            if not isinstance(p, dict):
                continue
            tr = (p.get('translation') or '').strip()
            if len(tr) < 20:
                continue
            label = p.get('label') or p.get('canvas_label') or ('Page %s' % p.get('page', i + 1))
            if p.get('volume_title'):
                label = '%s · %s' % (p['volume_title'], label)
            idx.append((name, i, label, tr.lower(), tr, p.get('image', '')))
    return idx


def _snippet(text, words, width=220):
    import re
    low = text.lower()
    found = [m.start() for m in (re.search(r'\b' + re.escape(w), low) for w in words) if m]
    pos = min(found or [0])
    start = max(0, pos - width // 3)
    out = text[start:start + width].replace('\n', ' ')
    return ('…' if start else '') + out + ('…' if start + width < len(text) else '')


@app.route('/api/pages/search')
def api_pages_search():
    q = (request.args.get('q') or '').strip().lower()
    words = [w for w in q.split() if len(w) >= 3] or ([q] if q else [])
    if not words:
        return jsonify({'q': q, 'total': 0, 'results': []})
    import re
    pats = [re.compile(r'\b' + re.escape(w)) for w in words]   # word starts: "sage" finds sage/sages, not passage
    hits = []
    for name, i, label, hay, tr, img in load_page_index():
        counts = [len(p.findall(hay)) for p in pats]
        n = sum(1 for c in counts if c)
        if n:
            hits.append((n * 100 + min(sum(counts), 50), name, i, label, tr, img))
    hits.sort(key=lambda h: -h[0])
    full = [h for h in hits if h[0] >= len(words) * 100]
    use = full if full else hits
    return jsonify({'q': q, 'total': len(use), 'results': [
        {'file': name, 'index': i, 'label': label, 'image': img, 'snippet': _snippet(tr, words)}
        for _, name, i, label, tr, img in use[:60]]})


# ── Mobile app API ─────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=1)
def load_books():
    with open('static/data/books.json', encoding='utf-8') as f:
        return json.load(f)['books']


@functools.lru_cache(maxsize=1)
def load_corpus():
    segs = []
    for i in (1, 2, 3):
        try:
            with open(f'static/data/corpus_shard_{i}.json', encoding='utf-8') as f:
                segs.extend(json.load(f).get('segments', []))
        except FileNotFoundError:
            pass
    bad = {'[PARSE ERROR]', '[SEGMENT FAILED]'}
    return [s for s in segs if s.get('translation') and (s.get('title_inferred') or '') not in bad]


_TRAD_NAMES = {'ahp': 'American Herbal Pharmacopoeia', 'commission_e': 'German Commission E', 'western_pharmacopeia': 'Western Pharmacopoeia',
               'western_european': 'Western European Herbals', 'central_european': 'Central European', 'italian_renaissance': 'Italian Renaissance',
               'japanese_honzo': 'Japanese Honzō', 'russian_slavic': 'Russian & Slavic', 'celtic_norse': 'Celtic & Norse', 'unani': 'Unani (Islamic)'}


def _trad_label(tid):
    if tid in _TRAD_NAMES:
        return _TRAD_NAMES[tid]
    t = load_traditions().get(tid)
    if t:
        return t.get('name') or tid
    return (tid or '').replace('_', ' ').title()


def _book_for_seg(seg):
    ck, tr = seg.get('_corpusKey') or '', seg.get('_tradition') or ''
    for b in load_books():
        for k in b.get('corpusKeys') or []:
            if ck and (ck.startswith(k) or k.startswith(ck)):
                return b
    for b in load_books():
        if tr and b.get('tradition') == tr:
            return b
    return None


def _words(q):
    q = (q or '').strip().lower()
    return [w for w in q.split() if len(w) >= 3] or ([q] if q else [])


def _rank(items, words, fields_title, fields_body):
    import re
    pats = [re.compile(r'\b' + re.escape(w)) for w in words]
    out = []
    for it in items:
        th = ' '.join(str(f(it) or '') for f in fields_title).lower()
        bh = ' '.join(str(f(it) or '') for f in fields_body).lower()
        n = t = 0
        for p in pats:
            a, b = bool(p.search(th)), bool(p.search(bh))
            n += a or b
            t += a
        if n:
            out.append((n * 100 + t * 30 + (1000 if n == len(pats) else 0), it))
    out.sort(key=lambda x: -x[0])
    full = [it for sc, it in out if sc >= 1000]
    return full if full else [it for sc, it in out]


def _plant_light(p):
    return {'id': p['id'], 'name': p.get('common_name'), 'botanical': p.get('modern_botanical'),
            'family': p.get('family'), 'areas': p.get('therapeutic_areas') or [],
            'badge': p.get('evidence_badge'), 'traditions': p.get('traditions') or [],
            'convergence': p.get('convergence_score') or 0, 'curated': bool(p.get('entries')),
            'image': ('/static/images/plants/%s.jpg' % p['id']) if os.path.exists('static/images/plants/%s.jpg' % p['id']) else None}


@app.route('/api/m/plants')
def api_m_plants():
    return jsonify({'plants': [_plant_light(p) for p in load_plants()]})


@app.route('/api/m/plant/<plant_id>')
def api_m_plant(plant_id):
    p = find_plant(plant_id)
    if not p:
        abort(404)
    d = dict(p)
    d['image'] = _plant_light(p)['image']
    d['tradition_labels'] = {t: _trad_label(t) for t in p.get('traditions') or []}
    return jsonify(d)


@app.route('/api/m/books')
def api_m_books():
    keep = ('id', 'title', 'short', 'tradition', 'date', 'year', 'language', 'author', 'cover', 'color',
            'description', 'hasManuscriptScans', 'manuscriptDataFile', 'manuscriptVolumesFile', 'totalEntries')
    books = [{k: b.get(k) for k in keep if b.get(k) is not None} for b in load_books()]
    for b in books:
        b['tradition_label'] = _trad_label(b.get('tradition'))
    return jsonify({'books': books})


@app.route('/api/m/traditions')
def api_m_traditions():
    out = {tid: {'name': t.get('name') or tid, 'color': t.get('color') or '#6A7A6E'} for tid, t in load_traditions().items()}
    for b in load_books():
        tid = b.get('tradition')
        if tid and tid not in out:
            out[tid] = {'name': _trad_label(tid), 'color': b.get('color') or '#6A7A6E'}
    # plants use some tradition ids that only appear there
    for p in load_plants():
        for tid in p.get('traditions') or []:
            out.setdefault(tid, {'name': _trad_label(tid), 'color': '#6A7A6E'})
    return jsonify(out)


@app.route('/api/m/book/<book_id>/passages')
def api_m_book_passages(book_id):
    b = next((x for x in load_books() if x['id'] == book_id), None)
    if not b:
        abort(404)
    keys = b.get('corpusKeys') or []
    segs = [s for s in load_corpus() if any((s.get('_corpusKey') or '').startswith(k) or k.startswith(s.get('_corpusKey') or '\0') for k in keys)]
    off = int(request.args.get('offset', 0))
    return jsonify({'total': len(segs), 'offset': off, 'passages': [_passage(s) for s in segs[off:off + 20]]})


def _passage(s, words=None):
    b = _book_for_seg(s)
    tr = s.get('translation') or ''
    return {'label': s.get('_label'), 'title': s.get('title_inferred'), 'translation': tr,
            'snippet': _snippet(tr, words) if words else tr[:240] + ('…' if len(tr) > 240 else ''),
            'original': s.get('original_text'), 'preparation': s.get('preparation'), 'condition': s.get('condition'),
            'ai_synth': bool(s.get('_ai_synthesized_disclosure')),
            'book': b['id'] if b else None, 'book_short': (b.get('short') or b.get('title')) if b else _trad_label(s.get('_tradition')),
            'color': b.get('color') if b else None, 'tradition': _trad_label(s.get('_tradition'))}


@app.route('/api/m/search')
def api_m_search():
    q = (request.args.get('q') or '').strip()
    words = _words(q)
    if not words:
        return jsonify({'q': q, 'plants': [], 'passages': [], 'passages_total': 0})
    plants = _rank(load_plants(), words,
                   [lambda p: p.get('common_name'), lambda p: p.get('modern_botanical'), lambda p: ' '.join((p.get('tradition_names') or {}).values())],
                   [lambda p: p.get('family'), lambda p: ' '.join(p.get('therapeutic_areas') or []).replace('_', ' '),
                    lambda p: ' '.join(e.get('condition') or '' for e in (p.get('entries') or {}).values())])
    segs = _rank(load_corpus(), words, [lambda s: s.get('title_inferred')], [lambda s: s.get('translation'), lambda s: s.get('condition')])
    return jsonify({'q': q, 'plants': [_plant_light(p) for p in plants[:30]], 'plants_total': len(plants),
                    'passages': [_passage(s, words) for s in segs[:40]], 'passages_total': len(segs)})


@app.route('/api/m/passage')
def api_m_passage():
    label = request.args.get('label')
    s = next((x for x in load_corpus() if x.get('_label') == label), None)
    if not s:
        abort(404)
    return jsonify(_passage(s))


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
