# Plantacopia STATUS — 2026-08-02

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
