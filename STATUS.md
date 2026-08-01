# Plantacopia STATUS — 2026-08-01

## Live state
- Corpus: 2,844 segments across 3 shards
- Library: 34 books, 12 civilizations, 34 traditions
- Manuscript pages: 1,423 Dongui + 202 Erbario + 448 Matthioli + 546 Leechdoms + 279 Bald's Leechbook

## Recently completed
- Dongui Bogam: all 25 volumes ingested, 1,423 pages (838 → 1,423 after extension passes)
- Erbario: 202/205 pages (full)
- Forge jobs: #216-220, #222-223 all 100% complete
- Job #224 South African: completed
- OCR cleanup: 145 fields cleaned (English traditions only)
- getTradColor enhanced: covers italian_renaissance, russian_slavic, commission_e, ahp, etc.
- openBook() wired to readerSetupLayers + readerLoadManuscriptPage

## Remaining
- Job #224 South African: add to corpus when complete (if not done above)
- Vol 16 Tangaekpyeon Vol.1: only 31pp (CDN issue on path 0/0f) — may need retry
- Dongui pages: many volumes capped at 60-64 (Wikimedia serves max ~60-64pp per PDF)
- Add tradition dot colors to tab bar legend (currently using BOOKS.color via getTradColor)
