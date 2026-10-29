# Plantacopia STATUS — 2026-10-28

## Mobile app (2026-10-29)
- Phones get static/m/ (index.html, m.css, m.js) at "/" (UA check in app.py); "Full site" link sets cookie pc_view=full
  (/?view=full); /m always serves the mobile app and clears the cookie.
- Four destinations: Search (plants / passages / manuscript pages), Plants (filter by use, sort by traditions or A-Z),
  Library (books by tradition, manuscript reader with swipe, image lightbox), Saved (localStorage).
- API: /api/m/plants, /api/m/plant/<id>, /api/m/books, /api/m/traditions, /api/m/search, /api/m/book/<id>/passages,
  /api/m/passage?label=. Search runs server-side (no 10 MB corpus download on phones).
- static/data/books.json is exported from BOOKS in index.html: run `node scripts/export_books.js` after editing BOOKS.

## Oedio translations (2026-10-28)
- scripts/sync_oedio_translations.py copies Oedio's page-level transcriptions + English translations into
  static/reader-data (fields: text = original, translation = English, label, language). Matches existing
  Plantacopia scans by image URL; replaces a file when Oedio has a larger/complete scan set. Re-run after
  each Oedio forge batch: `python3 scripts/sync_oedio_translations.py ~/oedio`
- 27 books + 11 Dongui Bogam volumes; 6 new BOOKS entries (Florentine Codex XI, Honzo Zufu, Honzo Wamyo,
  three Czech medical MSS); 16 existing books now open their scans (hasManuscriptScans + manuscriptDataFile).
- Manuscript reader shows the English translation with the original in a collapsible block.
- /api/pages/search (app.py) searches all translated pages server-side (word-start match); global search
  shows a "Manuscript pages" block whose rows open the reader at that page (split view).
- dongui_ms now loads all volumes via manuscriptVolumesFile (dongui-alignment.json).
- Pending: Vienna Dioscurides, Honzo Zufu, Ishinpo and the Czech MSS are still being translated in Oedio;
  re-run the sync when that forge run finishes.

# Earlier — 2026-08-02

## Live site
- URL: plantacopia.com / wholeplantcatalog.com
- Corpus: 2,844 segments, 3 shards
- Library: 34 books, 34 traditions, 12 civilizations
- Manuscript pages: 1,423 Dongui + 202 Erbario + 448 Matthioli + 546 Leechdoms + 279 Bald's Leechbook
- Last commit: 28069346

## What was fixed this session
- [x] 19 book covers updated — zero duplicates, all historically appropriate vintage images
- [x] Footer moved to true bottom (flex column body, margin-top:auto)
- [x] Library section removed from home tab
- [x] Search boxes: white text #FFFFFF, min-height 3rem, placeholder #7A6A50
- [x] Traditions tab: renderTraditionsTab() called on tab switch, openBookById() links work
- [x] Modern Research tab: 9 scientific query cards across 4 sections + custom query input
- [x] getTradColor EXTRA map: covers italian_renaissance, russian_slavic, welsh_celtic, japanese_honzo, commission_e, ahp, southern_african
- [x] Passage counts: 2,844 everywhere (was 2,867 in DB tab header)
- [x] Traditions header: "34 Traditions" (was "23 Traditions")
- [x] Stat tile: shows 34 from BOOKS at runtime
- [x] Corpus shards rebuilt with all Forge jobs: Welsh, Russian, Yamato, Norse, Honzo b2, Bencao 8+9, South African
- [x] Dongui Bogam: all 25 volumes, 1,423 pages (vs 838 at session start)
- [x] Erbario: 202 pages (full)
- [x] Function deduplication: renderTraditionsTab and runResearchQuery each appear exactly 1x

## Remaining (minor)
- Dongui Vol 16 (Tangaekpyeon Vol.1): 31 pages (CDN path 0/0f is slow; other vols 50-64pp)
- Plant Database tab could show books as cover-image cards (currently text list only)
- openBook() should eventually load the full split-panel manuscript reader for all books
