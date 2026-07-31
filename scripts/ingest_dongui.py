#!/usr/bin/env python3
"""
ingest_dongui.py — Ingest Dongui Bogam (東醫寶鑑) 25 volumes from Wikimedia Commons
into Plantacopia's reader-data contract: [{page, text, image, volume, volume_title}]

All 25 volumes are on Wikimedia Commons as PDFs from the National Library of Korea:
CNTS-00047967907_{N}_東醫寶鑑.pdf (N = 1..25)

Usage: python3 scripts/ingest_dongui.py [vol_start] [vol_end]
       python3 scripts/ingest_dongui.py         # all 25 volumes
       python3 scripts/ingest_dongui.py 21 25   # just volumes 21-25 (Tangaekpyeon / herbal)

Output: static/reader-data/dongui-vol-{N:02d}.json per volume
        static/reader-data/dongui-alignment.json  (volume metadata + page ranges)

The 25 volumes are divided into 5 sections:
  Naegyeongpyeon (内景篇) Internal Medicine  — vols 1–4
  Oehyeongpyeon  (外形篇) External Medicine  — vols 5–9
  Japbyeongpyeon (雜病篇) Miscellaneous      — vols 10–15
  Tangaekpyeon   (湯液篇) Herbal Medicine    — vols 16–22  ← most relevant for Plantacopia
  Chimgupyeon    (鍼灸篇) Acupuncture        — vols 23–25
"""
import json, sys, os, re, time
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Plantacopia/1.0 (noel@harmonyball.com; ingesting public-domain Korean National Library scans)'}

VOLUMES = {
    1:  ('Naegyeongpyeon Vol.1', '내경편 1권', 'internal'),
    2:  ('Naegyeongpyeon Vol.2', '내경편 2권', 'internal'),
    3:  ('Naegyeongpyeon Vol.3', '내경편 3권', 'internal'),
    4:  ('Naegyeongpyeon Vol.4', '내경편 4권', 'internal'),
    5:  ('Oehyeongpyeon Vol.1', '외형편 1권', 'external'),
    6:  ('Oehyeongpyeon Vol.2', '외형편 2권', 'external'),
    7:  ('Oehyeongpyeon Vol.3', '외형편 3권', 'external'),
    8:  ('Oehyeongpyeon Vol.4', '외형편 4권', 'external'),
    9:  ('Oehyeongpyeon Vol.5', '외형편 5권', 'external'),
    10: ('Japbyeongpyeon Vol.1', '잡병편 1권', 'misc'),
    11: ('Japbyeongpyeon Vol.2', '잡병편 2권', 'misc'),
    12: ('Japbyeongpyeon Vol.3', '잡병편 3권', 'misc'),
    13: ('Japbyeongpyeon Vol.4', '잡병편 4권', 'misc'),
    14: ('Japbyeongpyeon Vol.5', '잡병편 5권', 'misc'),
    15: ('Japbyeongpyeon Vol.6', '잡병편 6권', 'misc'),
    16: ('Tangaekpyeon Vol.1',   '탕액편 1권', 'herbal'),
    17: ('Tangaekpyeon Vol.2',   '탕액편 2권', 'herbal'),
    18: ('Tangaekpyeon Vol.3',   '탕액편 3권', 'herbal'),
    19: ('Tangaekpyeon Vol.4',   '탕액편 4권', 'herbal'),
    20: ('Tangaekpyeon Vol.5',   '탕액편 5권', 'herbal'),
    21: ('Tangaekpyeon Vol.6',   '탕액편 6권', 'herbal'),
    22: ('Tangaekpyeon Vol.7',   '탕액편 7권', 'herbal'),
    23: ('Chimgupyeon Vol.1',    '침구편 1권', 'acupuncture'),
    24: ('Chimgupyeon Vol.2',    '침구편 2권', 'acupuncture'),
    25: ('Chimgupyeon Vol.3',    '침구편 3권', 'acupuncture'),
}

def get_wikimedia_pdf_url(vol_n):
    """Get the PDF download URL for volume N from Wikimedia Commons."""
    fname = f'CNTS-00047967907 {vol_n} \u6771\u91ab\u5bf3\u9451.pdf'
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{urllib.parse.quote(fname)}&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            for pid, page in d.get('query',{}).get('pages',{}).items():
                if int(pid) > 0:
                    ii = page.get('imageinfo',[{}])
                    if ii and ii[0].get('url'):
                        return ii[0]['url']
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    return None

def extract_pdf_page_images(pdf_url, vol_n):
    """
    For each page of the PDF, construct a Wikimedia thumbnail URL.
    Wikimedia supports: https://upload.wikimedia.org/wikipedia/commons/thumb/{path}/{filename}/page{N}-{W}px-{filename}.jpg
    We use width=800 for good resolution in the split-panel reader.
    """
    # Parse the URL to get the path components
    # URL format: https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/{encoded_filename}.pdf
    import re as _re
    m = _re.match(r'https://upload\.wikimedia\.org/wikipedia/commons/([a-f0-9]/[a-f0-9]{2})/(.+\.pdf)', pdf_url)
    if not m:
        print(f"  Vol {vol_n}: could not parse URL {pdf_url}")
        return []
    
    path = m.group(1)
    filename = m.group(2)
    base = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{path}/{filename}"
    
    # We don't know page count upfront. Try up to 60 pages (most volumes are 20-50pp).
    pages = []
    for pg in range(1, 61):
        thumb_url = f"{base}/page{pg}-800px-{filename}.jpg"
        pages.append({'page': pg, 'image': thumb_url, 'text': '', 'volume': vol_n,
                      'volume_title': VOLUMES[vol_n][0], 'section': VOLUMES[vol_n][2]})
    return pages

def verify_pages(pages, max_workers=10):
    """Verify which page thumbnail URLs actually exist (HTTP 200)."""
    def check(p):
        req = urllib.request.Request(p['image'], headers=UA, method='HEAD')
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status == 200
        except:
            return False
    
    valid = []
    # Use binary search to find last valid page, then verify all up to that
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(check, pages))
    for p, ok in zip(pages, results):
        if ok:
            valid.append(p)
        elif valid:  # first gap after finding some — stop
            break
    return valid

def ingest_volume(vol_n):
    """Ingest a single volume."""
    print(f"\nVol {vol_n:2d}: {VOLUMES[vol_n][0]}")
    
    pdf_url = get_wikimedia_pdf_url(vol_n)
    if not pdf_url:
        print(f"  ERROR: no PDF URL found")
        return None
    print(f"  PDF: {pdf_url[:80]}")
    
    all_pages = extract_pdf_page_images(pdf_url, vol_n)
    print(f"  Checking up to {len(all_pages)} page thumbnails...")
    valid = verify_pages(all_pages)
    print(f"  Valid pages: {len(valid)}")
    
    os.makedirs('static/reader-data', exist_ok=True)
    path = f'static/reader-data/dongui-vol-{vol_n:02d}.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(valid, f, ensure_ascii=False)
    print(f"  Saved: {path} ({len(valid)} pages)")
    return valid

def main():
    args = sys.argv[1:]
    if len(args) >= 2:
        vol_range = range(int(args[0]), int(args[1])+1)
    elif len(args) == 1:
        vol_range = range(int(args[0]), int(args[0])+1)
    else:
        vol_range = range(1, 26)
    
    alignment = []
    page_offset = 0
    for n in vol_range:
        pages = ingest_volume(n)
        if pages:
            alignment.append({
                'volume': n,
                'title_en': VOLUMES[n][0],
                'title_ko': VOLUMES[n][1],
                'section': VOLUMES[n][2],
                'page_count': len(pages),
                'page_offset': page_offset,
                'data_file': f'dongui-vol-{n:02d}.json',
            })
            page_offset += len(pages)
        time.sleep(0.5)  # be polite to Wikimedia
    
    # Update alignment file
    align_path = 'static/reader-data/dongui-alignment.json'
    if os.path.exists(align_path):
        with open(align_path) as f:
            existing = json.load(f)
        # Merge
        existing_vols = {e['volume'] for e in existing}
        merged = [e for e in existing if e['volume'] not in {a['volume'] for a in alignment}] + alignment
        merged.sort(key=lambda x: x['volume'])
        alignment = merged
    
    with open(align_path, 'w', encoding='utf-8') as f:
        json.dump(alignment, f, ensure_ascii=False, indent=2)
    print(f"\nAlignment saved: {align_path}")
    print(f"Volumes ingested: {[a['volume'] for a in alignment]}")
    total = sum(a['page_count'] for a in alignment)
    print(f"Total pages: {total}")

if __name__ == '__main__':
    main()
