# Plantacopia — Project Status

Last updated: 2026-07-31

## Recently completed

- Search: runGlobalSearch() now creates modal dynamically — gold line bug permanently fixed
- Commission E (126 herbs, jobs #204-208, all 100%) and AHP (45 herbs, jobs #209-210, all 100%) ingested into corpus
- Corpus shards rebuilt: 2,752 total segments across 25 traditions
- Dongui Bogam (東醫寶鑑): all 25 volumes ingested from Wikimedia Commons (NLK scans)
  - static/reader-data/dongui-vol-01.json through dongui-vol-25.json
  - static/reader-data/dongui-alignment.json (volume metadata)
  - Book added to BOOKS array as id:'dongui_ms' with hasManuscriptScans:true
- Oedio reader features ported to Plantacopia reader:
  - Sepia toggle (readerToggleSepia)
  - Font size controls (readerFontSize)
  - Read-aloud / TTS (readerToggleTTS using Web Speech API)
  - Print dialog (readerDoPrint with clean print CSS)
  - Layer panel UI (readerToggleLayerPanel / readerSetLayer)
  - Manuscript image viewer (readerLoadManuscriptPage) with zoom overlay
- Scripts: scripts/ingest_dongui.py added for future re-ingestion

## In progress / incomplete

- Dongui page counts are partial (rate-limiting from Wikimedia during concurrent HEAD checks)
  - Solution: run ingest_dongui.py with sequential requests from a local machine
  - Most volumes show 1-27 pages but actually have 30-60 pages in the PDFs
  - The actual thumbnail URLs work fine — just need more time to verify
- openBook() for dongui_ms needs wiring to load manuscript data:
  - Should fetch /data/dongui-alignment.json, then load per-volume JSON
  - readerSetupLayers() and readerLoadManuscriptPage() are ready but not called from openBook yet
  - NEXT: add to openBook() — check if book.hasManuscriptScans, fetch alignment, load vol 1 pages
- Page turn animation: Plantacopia uses CSS @keyframes readerTurnFwd/Back — already exists
  - Oedio's tissueSnapshotAndSwap is more polished — could replace later if desired
- Failed Forge jobs still pending retry: #200 Honzo b2, #201-202 Bencao 8+9, #203 Southern African
  - These all have input files in static/data/_forge_input_*.json
  - Just need to re-fire from NoelOS Forge

## Key URLs / IDs

- Live: plantacopia.com / wholeplantcatalog.com
- Repo: noelwiggins/materia-medica-americana
- Railway: plentyfish.ai project (different from main plantacopia deploy)
- Dongui source: Wikimedia Commons category 東醫寶鑑
  - File pattern: CNTS-00047967907_{N}_東醫寶鑑.pdf (N=1..25)
  - Thumb pattern: /thumb/{path}/{filename}/page{N}-500px-{filename}.jpg
  - Note: 500px works, 800px returns 400 Bad Request
