# Plantacopia STATUS

Last updated: 2026-07-31

## Live state

- URL: plantacopia.com / wholeplantcatalog.com
- Repo: noelwiggins/materia-medica-americana
- Corpus: 2,867 segments across 3 shards (shard 1-3)
- Library: 34 books, 12 civilizations
- Traditions: 34 (Celtic/Norse, Italian/Renaissance, Russian/Slavic, Japanese, Korean, Chinese, Ayurveda, Egyptian, Unani, Tibetan, Mesoamerican, African, Amazonian, N.American, Philippine, Australian, WHO, Commission E, AHP, Welsh, Norse)

## Completed this session

- OCR garble cleanup: 145 fields cleaned across 3 corpus shards (English-language entries only; non-Latin scripts skipped)
- Forge jobs #216-219 all 100%: Welsh Myddfai, Russian Travnik, Yamato Honzo, Norse Scandinavian
- New books added (34 total): Bald Leechbook, Anglo-Saxon Leechdoms, Italian Erbario, Matthioli 1544, Welsh Myddfai, Russian Travnik, Yamato Honzo, Norse Medicine
- Manuscript reader wired: openBook() -> readerSetupLayers() -> readerLoadManuscriptPage()
- Frontispiece updated: "34 traditions · 2,867 passages · 12 civilizations"
- Search eyebrow updated: "2,867 passages across 34 traditions"
- Forge retries fired: #220 Honzo b2, #221 South African, #222 Bencao b8, #223 Bencao b9

## Forge running

- #220 Honzo Wamyo batch 2 — running
- #221 South African medicine — running
- #222 Bencao Gangmu batch 8 (rebuilt input) — running
- #223 Bencao Gangmu batch 9 (rebuilt input) — running
- After completion: rebuild shards to add new passages

## Reader-data manuscript files

- balds-leechbook.json: 279 pages (BL IIIF)
- leechdoms-anglo-saxon.json: 546 pages
- leechdoms-vol2-bl.json: 23 pages
- erbario-italian.json: 46 pages (rate-limited; 205 available)
- matthioli-dioscorides-1544.json: 448 pages
- dongui-vol-01 through 25: 147 pages total (rate-limited; need sequential re-ingest)

## Known issues

1. Dongui Bogam page counts low (1-27pp per volume) due to Wikimedia rate-limiting
   - Fix: run scripts/ingest_dongui.py sequentially (not concurrent)
   - All URLs confirmed working at 500px size
2. Erbario: 46/205 pages captured (same issue)
3. East African (job #221) fired incorrectly — input was south_african file
   - Check output after job completes and verify it has Southern African content
4. Bencao b8+9 already in corpus (38+43 segs) from earlier unknown source
   - New jobs #222-223 will add 25+25 more entries each — no harm
5. "See this plant in other books" — needs end-to-end test with new traditions

## Key patterns

- Manuscript page URL (IA): archive.org/download/{id}/page/n{N-1}/mode/2up
- Manuscript page URL (Wikimedia PDF): /thumb/{a/bc}/{filename.pdf}/page{N}-500px-{filename.pdf}.jpg
- IIIF image URL (BL): {service_base}/full/600,/0/default.jpg
- Corpus segment required fields: title_inferred, translation, _tradition, _corpusKey
- OCR cleanup: skip traditions in NON_ENGLISH_TRADITIONS set (Korean, Chinese, Arabic, Sanskrit, Tibetan, Japanese)
