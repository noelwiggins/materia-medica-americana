#!/usr/bin/env python3
"""Copy Oedio's page-level herbal transcriptions and English translations into Plantacopia.

Oedio (noelwiggins/oedio) keeps each digitized book as three aligned files in static/reader-data/:
  {slug}.json                 facsimile pages  [{page, image, text}]
  {slug}-transcription.json   original-language text per page (AI transcription)
  {slug}-english.json         English per page (AI translation)

Plantacopia's manuscript reader reads static/reader-data/{file}.json pages. This script writes, for every
herbal or medical book listed in MAP, pages carrying:
  text         the original-language transcription
  translation  the English translation
  label        the page label (folio etc.) where Oedio has one
Pages are matched to an existing Plantacopia file by image URL (so a Plantacopia file with fewer pages of the
same scans keeps its own order); when Oedio has more pages of the same scans, or a different and complete
scan set, Oedio's page list replaces the file. Re-runnable: run it again whenever Oedio's forge adds pages.

Usage: python3 scripts/sync_oedio_translations.py /path/to/oedio
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "reader-data")

# oedio slug -> (plantacopia reader-data file, plantacopia book id, language of the original)
MAP = [
    ("czech-herbal-XVII-J-28", "czech-herbal-XVII-J-28.json", "czech_herbal", "Old Czech / Latin"),
    ("matthioli-dioscorides-1544", "matthioli-dioscorides-1544.json", "matthioli_1544", "Italian"),
    ("erbario-italian", "erbario-italian.json", "erbario_italian", "Latin / Veneto"),
    ("leechdoms-cockayne", "leechdoms-anglo-saxon.json", "leechdoms", "Old English"),
    ("balds-leechbook-ms", "balds-leechbook.json", "balds_leechbook", "Old English"),
    ("badianus-manuscript", "badianus-manuscript.json", "badianus", "Latin"),
    ("bencao-jing", "bencao-jing.json", "bencaojing", "Classical Chinese"),
    ("canon-avicenna", "canon-avicenna.json", "canon", "Arabic"),
    ("charaka-samhita", "charaka-samhita.json", "charaka", "Sanskrit"),
    ("cobo-historia", "cobo-historia.json", "cobo", "Spanish"),
    ("ebers-papyrus", "ebers-papyrus.json", "ebers", "Egyptian (hieratic)"),
    ("honzo-wamyo", "honzo-wamyo.json", "honzo_wamyo", "Classical Chinese / Japanese"),
    ("yamato-honzo", "yamato-honzo.json", "yamato_honzo", "Classical Japanese / Kanbun"),
    ("kampo-tradition", "kampo-ishinpo.json", "kampo", "Classical Chinese (kanbun)"),
    ("maya-medicine", "ritual-of-the-bacabs.json", "maya", "Yucatec Maya"),
    ("norse-medicine", "harpestraeng-simplicibus.json", "norse_scandinavian", "Latin / Old Danish"),
    ("north-american-medicine", "schoepf-materia-medica-1787.json", "north_american", "Latin"),
    ("persian-avestan", "zend-avesta-vol2.json", "persian", "French / Avestan"),
    ("philippine-medicine", "flora-de-filipinas-1837.json", "philippine", "Spanish"),
    ("tibetan-gyushi", "gyushi-commentary.json", "tibetan", "Tibetan"),
    ("welsh-myddfai", "physicians-of-myddvai.json", "welsh_myddfai", "Middle Welsh / English"),
    ("florentine-codex-book11", "florentine-codex-book11.json", "florentine_book11", "Spanish / Nahuatl"),
    ("dioscorides-materia-medica", "vienna-dioscurides.json", "dioscorides", "Byzantine Greek"),
    ("bencao-gangmu", "honzo-zufu.json", "honzo_zufu", "Japanese"),
    ("medical-compendium-XVII-G-9", "medical-compendium-XVII-G-9.json", "czech_medical_compendium", "Latin"),
    ("prager-wundarznei-XVI-F-2", "prager-wundarznei-XVI-F-2.json", "prager_wundarznei", "Early New High German"),
    ("astronomical-medical-VI-F-7", "astronomical-medical-VI-F-7.json", "czech_astro_medical", "Latin"),
]
# Dongui Bogam: Oedio has some of the 25 volumes; they map onto Plantacopia's dongui-vol-NN.json by the volume
# number in the Wikimedia PDF name.
DONGUI = ["dongui-bogam-internal-%d" % i for i in range(1, 5)] + ["dongui-bogam-herbal-%d" % i for i in range(16, 23)]

DASH = "—"


def key(url):
    """Identify a scan independent of the size it was requested at."""
    u = (url or "").split("?")[0]
    if "/full/" in u:
        return u.split("/full/")[0]
    u = re.sub(r"/page(\d+)-\d+px-", r"/page\1-", u)
    u = re.sub(r"/\d+px-", "/", u)
    return u


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def clean(t):
    t = (t or "").strip()
    return "" if t == DASH else t


def oedio_pages(oedio, slug):
    rd = os.path.join(oedio, "static", "reader-data")
    base = load(os.path.join(rd, slug + ".json")) or []
    tr = {p["page"]: p for p in (load(os.path.join(rd, slug + "-transcription.json")) or [])}
    en = {p["page"]: p for p in (load(os.path.join(rd, slug + "-english.json")) or [])}
    pages = []
    for p in base:
        n = p["page"]
        t = clean(tr.get(n, {}).get("text")) or clean(p.get("text"))
        e = clean(en.get(n, {}).get("text"))
        pages.append({"page": n, "image": p.get("image", ""), "text": t, "translation": e,
                      "label": p.get("label") or tr.get(n, {}).get("label") or ""})
    return pages


def merge(existing, opages, language):
    """Return the new page list for a Plantacopia file."""
    ok = [p for p in opages if p["image"]]
    if existing:
        idx = {key(p.get("image")): i for i, p in enumerate(existing)}
        hits = sum(1 for p in ok if key(p["image"]) in idx)
        if hits >= 0.6 * len(existing) and len(ok) <= len(existing):
            out = [dict(p) for p in existing]
            for p in ok:
                i = idx.get(key(p["image"]))
                if i is None:
                    continue
                if p["text"]:
                    out[i]["text"] = p["text"]
                if p["translation"]:
                    out[i]["translation"] = p["translation"]
                if p["label"] and not out[i].get("label"):
                    out[i]["label"] = p["label"]
                out[i]["language"] = out[i].get("language") or language
            return out
        # Oedio's set is larger or a different scan: take it, carrying Plantacopia's shared page fields over
        shared = {k: v for k, v in existing[0].items()
                  if k not in ("page", "image", "text", "translation", "label", "canvas_label", "folio")
                  and all(q.get(k) == v for q in existing)}
    else:
        shared = {}
    out = []
    for i, p in enumerate(ok):
        q = {"page": i + 1, "image": p["image"], "text": p["text"], "translation": p["translation"],
             "language": shared.get("language") or language}
        if p["label"]:
            q["label"] = p["label"]
        for k, v in shared.items():
            q.setdefault(k, v)
        out.append(q)
    return out


def write(name, pages):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, separators=(",", ":"))


def main(oedio):
    report = []
    for slug, fname, book, lang in MAP:
        op = oedio_pages(oedio, slug)
        if not op:
            report.append((slug, "missing in oedio"))
            continue
        pages = merge(load(os.path.join(OUT, fname)), op, lang)
        write(fname, pages)
        report.append((fname, f"{sum(1 for p in pages if p.get('translation'))}/{len(pages)} pages translated"))
    # Dongui Bogam volumes
    align_path = os.path.join(OUT, "dongui-alignment.json")
    align = load(align_path) or []
    for slug in DONGUI:
        op = oedio_pages(oedio, slug)
        if not op:
            continue
        m = re.search(r"CNTS-\d+_(\d+)_", op[0]["image"])
        if not m:
            continue
        vol = int(m.group(1))
        fname = "dongui-vol-%02d.json" % vol
        pages = merge(load(os.path.join(OUT, fname)), op, "Classical Chinese / Korean")
        write(fname, pages)
        for a in align:
            if a.get("volume") == vol:
                a["page_count"] = len(pages)
        report.append((fname, f"{sum(1 for p in pages if p.get('translation'))}/{len(pages)} pages translated"))
    if align:
        with open(align_path, "w", encoding="utf-8") as f:
            json.dump(align, f, ensure_ascii=False, indent=2)
    for r in report:
        print("%-40s %s" % r)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/oedio"))
