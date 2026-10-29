/* Plantacopia mobile app. Hash routes:
   #/                 search home        #/search?q=…&tab=plants|passages|pages
   #/plants?area=…    plant list         #/plant/MMA-001
   #/library?t=…      books              #/book/<id>
   #/read/<id>/<n>    manuscript reader  #/passage?label=…
   #/saved                                                                        */
(function () {
  'use strict';
  var view = document.getElementById('view'), topbar = document.getElementById('topbar');
  var cache = {};
  var YEAR = new Date().getFullYear();

  // ── helpers ──────────────────────────────────────────────────────────
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function get(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { cache[url] = d; return d; });
  }
  function qs(hash) { var o = {}, i = hash.indexOf('?'); if (i < 0) return o; hash.slice(i + 1).split('&').forEach(function (kv) { var p = kv.split('='); if (p[0]) o[decodeURIComponent(p[0])] = decodeURIComponent((p[1] || '').replace(/\+/g, ' ')); }); return o; }
  function words(q) { return (q || '').toLowerCase().split(/\s+/).filter(function (w) { return w.length >= 3; }); }
  function hl(text, ws) {
    var h = esc(text);
    (ws || []).forEach(function (w) { h = h.replace(new RegExp('\\b(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'), '<mark>$1</mark>'); });
    return h;
  }
  function badge(b) {
    return String(b).toLowerCase().replace(/\b(fda|who|ema)\b/g, function (m) { return m.toUpperCase(); }).replace(/^./, function (c) { return c.toUpperCase(); });
  }
  // older forge output starts some pages with a bracketed reviewer note; show it as a caveat, not as text
  function splitCaveat(t) {
    var m = /^\s*\[(AI TRANSCRIPTION[^\]]*)\]\s*/i.exec(t || '');
    if (!m) return { caveat: '', text: t || '' };
    var c = m[1].replace(/^AI TRANSCRIPTION,?\s*/i, '').replace(/\s*--\s*NEEDS SCHOLARLY REVIEW:?\s*/i, ': ').replace(/^LOW CONFIDENCE/i, 'Low confidence');
    return { caveat: c, text: t.slice(m[0].length) };
  }
  function areaLabel(a) { var s = String(a).replace(/_/g, ' ').replace(/\bgeneral\b/, '').trim(); return s.charAt(0).toUpperCase() + s.slice(1); }
  var store = {
    read: function () { try { return JSON.parse(localStorage.getItem('pc_saved') || '{"plants":[],"pages":[]}'); } catch (e) { return { plants: [], pages: [] }; } },
    write: function (d) { try { localStorage.setItem('pc_saved', JSON.stringify(d)); } catch (e) {} }
  };
  function isSaved(kind, key) { return store.read()[kind].some(function (x) { return (x.key || x) === key; }); }
  function toggleSaved(kind, item) {
    var d = store.read(), key = item.key || item, i = d[kind].findIndex(function (x) { return (x.key || x) === key; });
    if (i >= 0) d[kind].splice(i, 1); else d[kind].unshift(item);
    store.write(d); return i < 0;
  }

  var TRAD = {};
  function tradColor(id) { return (TRAD[id] && TRAD[id].color) || '#6A7A6E'; }
  function tradName(id) { return (TRAD[id] && TRAD[id].name) || String(id || '').replace(/_/g, ' '); }
  function strip(trads, big) {
    var t = (trads || []).slice(0, 14);
    return '<div class="strip" aria-hidden="true">' + t.map(function (id) { return '<i style="background:' + tradColor(id) + '"></i>'; }).join('') + '</div>' +
      (big ? '' : '');
  }
  function stripLabel(n) { return n === 1 ? 'Recorded in 1 tradition' : 'Recorded independently in ' + n + ' traditions'; }

  // ── chrome ────────────────────────────────────────────────────────────
  var ICON = {
    back: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>',
    save: '<svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
    search: '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/></svg>'
  };
  function bar(title, opts) {
    opts = opts || {};
    topbar.innerHTML = (opts.back ? '<button class="icon-btn" data-back aria-label="Back">' + ICON.back + '</button>' : '') +
      '<div class="title">' + esc(title || '') + '</div>' + (opts.right || '');
    var b = topbar.querySelector('[data-back]');
    if (b) b.onclick = function () { if (history.length > 1) history.back(); else location.hash = opts.back; };
  }
  function nav(which) {
    document.querySelectorAll('#navbar a').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-nav') === which); });
  }
  function foot() { return '<div class="foot"><span>© ' + YEAR + ' Noel Wiggins. All rights reserved.</span><a href="/?view=full">Full site</a></div>'; }
  function loading() { view.innerHTML = '<div class="loading">Loading…</div>'; }

  // ── lightbox (images open here, never in a new tab) ───────────────────
  var lb = document.getElementById('lightbox'), lbScroll = lb.querySelector('.lb-scroll'), lbImg = lb.querySelector('img');
  function openLightbox(src, alt) {
    lbImg.src = src; lbImg.alt = alt || ''; lbScroll.classList.remove('zoom'); lb.hidden = false; document.body.style.overflow = 'hidden';
    history.pushState({ lb: 1 }, '');
  }
  function closeLightbox(fromPop) { if (lb.hidden) return; lb.hidden = true; document.body.style.overflow = ''; if (!fromPop) history.back(); }
  lb.querySelector('.lb-close').onclick = function () { closeLightbox(false); };
  var lastTap = 0;
  lbScroll.addEventListener('click', function (e) {
    var now = Date.now();
    if (now - lastTap < 320) {
      var zoom = !lbScroll.classList.contains('zoom'), r = lbImg.getBoundingClientRect();
      var fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
      lbScroll.classList.toggle('zoom', zoom);
      if (zoom) { lbScroll.scrollLeft = fx * lbImg.width - lbScroll.clientWidth / 2; lbScroll.scrollTop = fy * lbImg.height - lbScroll.clientHeight / 2; }
    }
    lastTap = now;
  });
  view.addEventListener('click', function (e) {
    var z = e.target.closest('[data-zoom]');
    if (z) { e.preventDefault(); openLightbox(z.getAttribute('data-zoom') || z.src, z.alt); }
  });

  // ── data ──────────────────────────────────────────────────────────────
  function plants() { return get('/api/m/plants').then(function (d) { return d.plants; }); }
  function books() { return get('/api/m/books').then(function (d) { return d.books; }); }

  // ── views ─────────────────────────────────────────────────────────────
  var QUICK = ['Fever', 'Sleep', 'Wounds', 'Digestion', 'Cough', 'Headache', 'Anxiety', 'Pain', 'Skin', 'Childbirth', 'Willow', 'Ginger', 'Garlic', 'Yarrow'];

  function searchHome() {
    nav('search'); bar('');
    topbar.innerHTML = '';
    view.innerHTML = '<div class="wordmark">Plantacopia</div>' +
      '<p class="wordmark-sub">What 34 healing traditions wrote about plants, from the original manuscripts.</p>' +
      searchBox('') +
      '<div class="chips">' + QUICK.map(function (q) { return '<a class="chip" href="#/search?q=' + encodeURIComponent(q.toLowerCase()) + '">' + q + '</a>'; }).join('') + '</div>' +
      '<h2 class="sec">Recorded by the most traditions</h2><p class="sec-note">Each mark is a tradition that documented the plant on its own.</p><div class="hscroll" id="top-plants"><div class="loading">Loading…</div></div>' +
      '<h2 class="sec">Read the sources</h2><p class="sec-note">Original manuscripts, page by page, with English translations.</p><div class="hscroll" id="top-books"></div>' +
      foot();
    wireSearch('');
    plants().then(function (ps) {
      var top = ps.filter(function (p) { return p.curated; }).sort(function (a, b) { return b.traditions.length - a.traditions.length || b.convergence - a.convergence; }).slice(0, 12);
      document.getElementById('top-plants').innerHTML = top.map(plantCard).join('');
    });
    books().then(function (bs) {
      var scans = bs.filter(function (b) { return b.hasManuscriptScans; });
      document.getElementById('top-books').innerHTML = scans.slice(0, 14).map(function (b) {
        return '<a class="pcard" href="#/book/' + esc(b.id) + '" style="width:150px;min-height:0;padding:12px">' +
          '<img class="cover" style="width:100%;height:170px;background:' + esc(b.color || '') + '" loading="lazy" src="' + esc(b.cover || '') + '" alt="" onerror="this.removeAttribute(\'src\')">' +
          '<span class="nm" style="font-size:16px">' + esc(b.short || b.title) + '</span><span class="dim">' + esc(b.date || b.year || '') + '</span></a>';
      }).join('');
    });
  }
  function searchBox(q) {
    return '<form class="searchbar" role="search" id="sform">' + ICON.search.replace('<svg', '<svg aria-hidden="true"') +
      '<input id="sinput" type="search" enterkeyhint="search" autocomplete="off" placeholder="A plant, an ailment, a remedy" value="' + esc(q) + '" aria-label="Search">' +
      (q ? '<button type="button" class="clear" aria-label="Clear">×</button>' : '') + '</form>';
  }
  function wireSearch(q) {
    var f = document.getElementById('sform'), inp = document.getElementById('sinput');
    f.onsubmit = function (e) { e.preventDefault(); var v = inp.value.trim(); if (v) location.hash = '#/search?q=' + encodeURIComponent(v); inp.blur(); };
    var c = f.querySelector('.clear'); if (c) c.onclick = function () { inp.value = ''; inp.focus(); };
  }
  function plantCard(p) {
    return '<a class="pcard" href="#/plant/' + esc(p.id) + '"><span class="nm">' + esc(p.name) + '</span>' +
      (p.botanical ? '<span class="bot">' + esc(p.botanical) + '</span>' : '') +
      strip(p.traditions) + '<span class="strip-label">' + p.traditions.length + ' traditions</span></a>';
  }
  function plantRow(p, ws) {
    return '<a class="row" href="#/plant/' + esc(p.id) + '">' +
      (p.image ? '<img class="thumb" loading="lazy" src="' + esc(p.image) + '" alt="">' : '') +
      '<div class="txt"><div class="nm">' + hl(p.name, ws) + '</div>' + (p.botanical ? '<div class="bot">' + hl(p.botanical, ws) + '</div>' : '') +
      '<div class="meta">' + strip(p.traditions) + (p.badge ? '<span class="badge">' + esc(badge(p.badge)) + '</span>' : '') + '</div></div></a>';
  }
  function passageRow(s, ws) {
    return '<div class="passage" data-label="' + esc(s.label) + '"><div class="src"><i style="background:' + esc(s.color || '#6A7A6E') + '"></i>' + esc(s.book_short || s.tradition) + '</div>' +
      '<h3>' + hl(s.title, ws) + '</h3><p>' + hl(s.snippet, ws) + '</p></div>';
  }

  function searchResults(params) {
    var q = params.q || '', tab = params.tab || '', ws = words(q);
    nav('search'); bar('', {}); topbar.innerHTML = '';
    view.innerHTML = '<div style="height:10px"></div>' + searchBox(q) + '<div id="sres"><div class="loading">Searching…</div></div>';
    wireSearch(q);
    Promise.all([get('/api/m/search?q=' + encodeURIComponent(q)), get('/api/pages/search?q=' + encodeURIComponent(q)).catch(function () { return { results: [], total: 0 }; }), books()])
      .then(function (r) {
        var d = r[0], pg = r[1], bs = r[2];
        var fileBook = {};
        bs.forEach(function (b) { if (b.manuscriptDataFile) fileBook[b.manuscriptDataFile] = b; });
        var pages = (pg.results || []).map(function (h) {
          var b = /^dongui-vol-/.test(h.file) ? bs.find(function (x) { return x.id === 'dongui_ms'; }) : fileBook[h.file];
          return b ? { b: b, h: h } : null;
        }).filter(Boolean);
        var counts = { plants: d.plants_total || 0, passages: d.passages_total || 0, pages: pg.total || 0 };
        if (!tab) tab = counts.plants ? 'plants' : counts.passages ? 'passages' : 'pages';
        var box = document.getElementById('sres');
        if (!counts.plants && !counts.passages && !counts.pages) {
          box.innerHTML = '<div class="empty"><b>Nothing found for “' + esc(q) + '”</b>Try a single word, such as a plant name or an ailment.</div>';
          return;
        }
        function seg(id, label) { return '<button data-tab="' + id + '" class="' + (tab === id ? 'on' : '') + '">' + label + ' ' + counts[id] + '</button>'; }
        var body = '';
        if (tab === 'plants') body = counts.plants ? '<div class="list">' + d.plants.map(function (p) { return plantRow(p, ws); }).join('') + '</div>' : '<div class="empty">No plants match. See passages or pages.</div>';
        if (tab === 'passages') body = (d.passages || []).map(function (s) { return passageRow(s, ws); }).join('') || '<div class="empty">No passages match.</div>';
        if (tab === 'pages') body = pages.length ? pages.map(function (x) {
          return '<a class="passage" style="display:block;text-decoration:none" href="#/read/' + esc(x.b.id) + '/' + (x.h.index + 1) + '?img=' + encodeURIComponent(x.h.image || '') + '">' +
            '<div class="src"><i style="background:' + esc(x.b.color || '#6A7A6E') + '"></i>' + esc(x.b.short || x.b.title) + ', ' + esc(x.h.label) + '</div><p>' + hl(x.h.snippet, ws) + '</p></a>';
        }).join('') + (pg.total > pages.length ? '<p class="dim">Showing the best ' + pages.length + ' of ' + pg.total + ' pages.</p>' : '') : '<div class="empty">No manuscript pages match.</div>';
        box.innerHTML = '<div class="seg" role="tablist">' + seg('plants', 'Plants') + seg('passages', 'Passages') + seg('pages', 'Pages') + '</div>' + body;
        box.querySelectorAll('.seg button').forEach(function (b) { b.onclick = function () { history.replaceState(null, '', '#/search?q=' + encodeURIComponent(q) + '&tab=' + b.getAttribute('data-tab')); route(); }; });
        box.querySelectorAll('.passage[data-label]').forEach(function (el) { el.onclick = function () { location.hash = '#/passage?label=' + encodeURIComponent(el.getAttribute('data-label')); }; });
      }).catch(function () { document.getElementById('sres').innerHTML = '<div class="empty"><b>Search is unavailable right now</b>Check your connection and try again.</div>'; });
  }

  function plantList(params) {
    nav('plants'); bar('Plants'); loading();
    plants().then(function (ps) {
      var area = params.area || '', sort = params.sort || 'traditions';
      var areas = {};
      ps.forEach(function (p) { p.areas.forEach(function (a) { areas[a] = (areas[a] || 0) + 1; }); });
      var top = Object.keys(areas).sort(function (a, b) { return areas[b] - areas[a]; }).slice(0, 16);
      var list = ps.filter(function (p) { return !area || p.areas.indexOf(area) >= 0; });
      if (sort === 'az') list.sort(function (a, b) { return a.name.localeCompare(b.name); });
      else list.sort(function (a, b) { return b.traditions.length - a.traditions.length || (b.curated - a.curated) || a.name.localeCompare(b.name); });
      var shown = list.slice(0, 80);
      view.innerHTML = '<div class="chips scroll"><a class="chip ' + (!area ? 'on' : '') + '" href="#/plants?sort=' + sort + '">All</a>' +
        top.map(function (a) { return '<a class="chip ' + (area === a ? 'on' : '') + '" href="#/plants?area=' + encodeURIComponent(a) + '&sort=' + sort + '">' + esc(areaLabel(a)) + '</a>'; }).join('') + '</div>' +
        '<div class="seg"><button data-s="traditions" class="' + (sort !== 'az' ? 'on' : '') + '">Most traditions</button><button data-s="az" class="' + (sort === 'az' ? 'on' : '') + '">A to Z</button></div>' +
        '<p class="dim">' + list.length + ' plants' + (area ? ' used for ' + esc(areaLabel(area).toLowerCase()) : '') + '</p>' +
        '<div class="list" id="plist">' + shown.map(function (p) { return plantRow(p); }).join('') + '</div>' +
        (list.length > shown.length ? '<button class="btn tonal block more" id="pmore">Show more plants</button>' : '') + foot();
      view.querySelectorAll('.seg button').forEach(function (b) { b.onclick = function () { location.hash = '#/plants?' + (area ? 'area=' + encodeURIComponent(area) + '&' : '') + 'sort=' + b.getAttribute('data-s'); }; });
      var n = shown.length, more = document.getElementById('pmore');
      if (more) more.onclick = function () { var next = list.slice(n, n + 80); n += next.length; document.getElementById('plist').insertAdjacentHTML('beforeend', next.map(function (p) { return plantRow(p); }).join('')); if (n >= list.length) more.remove(); };
    });
  }

  function plantDetail(id) {
    nav('plants'); bar('', { back: '#/plants' }); loading();
    get('/api/m/plant/' + encodeURIComponent(id)).then(function (p) {
      var saved = isSaved('plants', p.id);
      bar('', { back: '#/plants', right: '<button class="icon-btn ' + (saved ? 'on' : '') + '" id="savebtn" aria-label="' + (saved ? 'Remove from saved' : 'Save plant') + '">' + ICON.save + '</button>' });
      document.getElementById('savebtn').onclick = function () {
        var on = toggleSaved('plants', { key: p.id, name: p.common_name, botanical: p.modern_botanical });
        this.classList.toggle('on', on); this.setAttribute('aria-label', on ? 'Remove from saved' : 'Save plant');
      };
      var trads = p.traditions || [], mr = p.modern_research || {};
      var h = '<div class="hero"><h1>' + esc(p.common_name) + '</h1>' + (p.modern_botanical ? '<p class="bot">' + esc(p.modern_botanical) + '</p>' : '') +
        (p.family ? '<div class="fam">Family ' + esc(p.family) + '</div>' : '') +
        strip(trads) + '<span class="strip-label">' + stripLabel(trads.length) + ': ' + trads.map(function (t) { return esc((p.tradition_labels || {})[t] || tradName(t)); }).join(', ') + '</span></div>';
      if (p.image) h += '<img class="hero-img" src="' + esc(p.image) + '" alt="' + esc(p.common_name) + '" data-zoom>';
      if ((p.therapeutic_areas || []).length) h += '<h2 class="sec">Used for</h2><div class="chips">' + p.therapeutic_areas.map(function (a) { return '<a class="chip" href="#/plants?area=' + encodeURIComponent(a) + '">' + esc(areaLabel(a)) + '</a>'; }).join('') + '</div>';
      if (mr.summary || p.evidence_badge) {
        h += '<div class="evidence">' + (p.evidence_badge ? '<span class="badge">' + esc(badge(p.evidence_badge)) + '</span>' : '') +
          '<h3>What modern research found</h3>' + (mr.key_compound ? '<p><b>Key compound:</b> ' + esc(mr.key_compound) + '</p>' : '') +
          (mr.summary ? '<p>' + esc(mr.summary) + '</p>' : '') + (mr.significance ? '<p class="dim">' + esc(mr.significance) + '</p>' : '') +
          (p.evidence_authority ? '<p class="dim">' + esc(p.evidence_authority) + '</p>' : '') + '</div>';
      }
      var entries = p.entries || {};
      var keys = Object.keys(entries);
      if (keys.length) {
        h += '<h2 class="sec">In the sources</h2>';
        keys.forEach(function (t) {
          var e = entries[t] || {};
          h += '<div class="source"><div class="trad"><i style="background:' + tradColor(t) + '"></i>' + esc((p.tradition_labels || {})[t] || tradName(t)) +
            (e.source_text || e.book ? '<span class="dim" style="font-weight:400">, ' + esc(e.source_text || ('Book ' + e.book + (e.chapter ? ', ch. ' + e.chapter : ''))) + '</span>' : '') + '</div>' +
            ((p.tradition_names || {})[t] ? '<div class="localname">' + esc(p.tradition_names[t]) + '</div>' : '') +
            (e.translation ? '<p class="tr">' + esc(e.translation) + '</p>' : '') +
            (e.condition ? '<p class="kv"><b>For:</b> ' + esc(e.condition) + '</p>' : '') +
            (e.preparation ? '<p class="kv"><b>Preparation:</b> ' + esc(e.preparation) + '</p>' : '') +
            (e.original ? '<details class="orig"><summary>Original text</summary><div>' + esc(e.original) + '</div></details>' : '') +
            (e.notes ? '<p class="dim">' + esc(e.notes) + '</p>' : '') + '</div>';
        });
      }
      var links = p.corpus_links || [];
      if (links.length) {
        h += '<h2 class="sec">Mentioned in</h2>';
        links.forEach(function (l) {
          h += '<div class="source"><div class="trad"><i style="background:' + tradColor(l.tradition) + '"></i>' + esc(tradName(l.tradition)) + '</div>' +
            '<div class="localname" style="font-style:normal">' + esc(l.title || '') + '</div>' + (l.translation ? '<p class="tr">' + esc(l.translation) + '</p>' : '') +
            (l.original ? '<details class="orig"><summary>Original text</summary><div>' + esc(l.original) + '</div></details>' : '') + '</div>';
        });
      }
      if (p.stub_note) h += '<p class="dim" style="margin-top:20px">' + esc(p.stub_note) + '</p>';
      h += '<p style="margin-top:24px"><a class="btn tonal" href="#/search?q=' + encodeURIComponent((p.common_name || '').split(/[\/(]/)[0].trim().toLowerCase()) + '&tab=pages">Find it in the manuscripts</a></p>' + foot();
      view.innerHTML = h;
      bar('', { back: '#/plants', right: topbar.querySelector('#savebtn').outerHTML });
      var sb = document.getElementById('savebtn');
      sb.onclick = function () { var on = toggleSaved('plants', { key: p.id, name: p.common_name, botanical: p.modern_botanical }); sb.classList.toggle('on', on); };
    }).catch(function () { view.innerHTML = '<div class="empty"><b>This plant could not be loaded</b><a href="#/plants">Back to all plants</a></div>'; });
  }

  function library(params) {
    nav('library'); bar('Library'); loading();
    books().then(function (bs) {
      var t = params.t || '', groups = {};
      bs.forEach(function (b) { var k = b.tradition_label || b.tradition; (groups[k] = groups[k] || []).push(b); });
      var names = Object.keys(groups).sort();
      var list = bs.filter(function (b) { return !t || (b.tradition_label || b.tradition) === t; })
        .sort(function (a, b) { return (b.hasManuscriptScans ? 1 : 0) - (a.hasManuscriptScans ? 1 : 0) || a.title.localeCompare(b.title); });
      view.innerHTML = '<div class="chips scroll"><a class="chip ' + (!t ? 'on' : '') + '" href="#/library">All</a>' +
        names.map(function (n) { return '<a class="chip ' + (t === n ? 'on' : '') + '" href="#/library?t=' + encodeURIComponent(n) + '">' + esc(n) + '</a>'; }).join('') + '</div>' +
        '<p class="dim">' + list.length + ' books' + (t ? ' in ' + esc(t) : '') + '</p><div class="list">' +
        list.map(function (b) {
          return '<a class="row" href="#/book/' + esc(b.id) + '"><img class="cover" style="background:' + esc(b.color || '') + '" loading="lazy" src="' + esc(b.cover || '') + '" alt="" onerror="this.removeAttribute(\'src\')"><div class="txt">' +
            '<div class="nm">' + esc(b.title) + '</div><div class="dim">' + esc([b.date || b.year, b.language].filter(Boolean).join(', ')) + '</div>' +
            (b.hasManuscriptScans ? '<div class="meta"><span class="badge" style="background:var(--primary-soft);color:var(--ink)">Manuscript pages</span></div>' : '') + '</div></a>';
        }).join('') + '</div>' + foot();
    });
  }

  function bookDetail(id) {
    nav('library'); bar('', { back: '#/library' }); loading();
    books().then(function (bs) {
      var b = bs.find(function (x) { return x.id === id; });
      if (!b) { view.innerHTML = '<div class="empty"><b>Book not found</b><a href="#/library">Back to the library</a></div>'; return; }
      bar(b.short || b.title, { back: '#/library' });
      view.innerHTML = '<div class="bookhead"><img class="cover" style="background:' + esc(b.color || '') + '" src="' + esc(b.cover || '') + '" alt="" data-zoom onerror="this.removeAttribute(\'src\');this.removeAttribute(\'data-zoom\')"><div><h1>' + esc(b.title) + '</h1>' +
        '<div class="dim">' + esc(b.author || '') + '</div><div class="dim">' + esc([b.date || b.year, b.language].filter(Boolean).join(', ')) + '</div>' +
        '<div class="dim">' + esc(b.tradition_label || '') + '</div></div></div>' +
        (b.hasManuscriptScans ? '<a class="btn block" href="#/read/' + esc(b.id) + '/1">Read the manuscript</a>' : '') +
        (b.description ? '<p class="prose">' + esc(b.description) + '</p>' : '') +
        '<h2 class="sec">Passages</h2><p class="sec-note" id="pcount"></p><div id="plist"></div><button class="btn tonal block more" id="pmore" hidden>Show more passages</button>' + foot();
      var off = 0;
      function more() {
        get('/api/m/book/' + encodeURIComponent(id) + '/passages?offset=' + off).then(function (d) {
          document.getElementById('pcount').textContent = d.total ? d.total + ' translated passages from this source.' : 'No separate passages; read the manuscript pages above.';
          document.getElementById('plist').insertAdjacentHTML('beforeend', d.passages.map(function (s) { return passageRow(s); }).join(''));
          off += d.passages.length;
          var m = document.getElementById('pmore'); m.hidden = off >= d.total;
          document.querySelectorAll('#plist .passage').forEach(function (el) { el.onclick = function () { location.hash = '#/passage?label=' + encodeURIComponent(el.getAttribute('data-label')); }; });
        });
      }
      document.getElementById('pmore').onclick = more;
      more();
    });
  }

  function passage(params) {
    nav('search'); bar('', { back: '#/' }); loading();
    get('/api/m/passage?label=' + encodeURIComponent(params.label || '')).then(function (s) {
      bar(s.book_short || 'Passage', { back: s.book ? '#/book/' + s.book : '#/' });
      view.innerHTML = '<div class="hero" style="margin-bottom:8px"><div class="src dim" style="display:flex;gap:8px;align-items:center"><i style="width:10px;height:10px;border-radius:3px;background:' + esc(s.color || '#6A7A6E') + '"></i>' + esc(s.tradition) + '</div>' +
        '<h1 style="font-size:28px">' + esc(s.title) + '</h1></div>' +
        '<p class="rd-text">' + esc(s.translation) + '</p>' +
        (s.condition ? '<p class="kv"><b>For:</b> ' + esc(s.condition) + '</p>' : '') + (s.preparation ? '<p class="kv"><b>Preparation:</b> ' + esc(s.preparation) + '</p>' : '') +
        (s.original ? '<details class="orig"><summary>Original text</summary><div>' + esc(s.original) + '</div></details>' : '') +
        (s.ai_synth ? '<p class="rd-note">This entry is an AI-written overview, not a transcription of a published text.</p>' : '') +
        (s.book ? '<p style="margin-top:20px"><a class="btn tonal" href="#/book/' + esc(s.book) + '">More from this source</a></p>' : '') + foot();
    }).catch(function () { view.innerHTML = '<div class="empty"><b>This passage could not be loaded</b><a href="#/">Back to search</a></div>'; });
  }

  // ── reader ────────────────────────────────────────────────────────────
  var pagesCache = {};
  function loadPages(b) {
    if (pagesCache[b.id]) return Promise.resolve(pagesCache[b.id]);
    var p;
    if (b.manuscriptVolumesFile) {
      p = get('/reader-data/' + b.manuscriptVolumesFile).then(function (vols) {
        return Promise.all(vols.map(function (v) { return get('/reader-data/' + v.data_file).then(function (ps) { return ps.map(function (x) { return Object.assign({ volume_title: v.title_en }, x); }); }).catch(function () { return []; }); }));
      }).then(function (parts) { return [].concat.apply([], parts); });
    } else p = get('/reader-data/' + b.manuscriptDataFile);
    return p.then(function (ps) { pagesCache[b.id] = ps; return ps; });
  }
  var readerState = null;
  function reader(id, n, params) {
    document.body.classList.add('reading');
    bar('', { back: '#/book/' + id }); loading();
    books().then(function (bs) {
      var b = bs.find(function (x) { return x.id === id; });
      if (!b) { view.innerHTML = '<div class="empty"><b>Book not found</b></div>'; return; }
      return loadPages(b).then(function (pages) {
        var idx = Math.max(0, Math.min(pages.length - 1, (parseInt(n, 10) || 1) - 1));
        if (params.img) { var j = pages.findIndex(function (p) { return p.image === params.img; }); if (j >= 0) idx = j; history.replaceState(null, '', '#/read/' + id + '/' + (idx + 1)); }
        readerState = { b: b, pages: pages };
        showPage(idx);
      });
    }).catch(function () { view.innerHTML = '<div class="empty"><b>The pages could not be loaded</b>Check your connection and try again.</div>'; });
  }
  function showPage(idx) {
    var b = readerState.b, pages = readerState.pages, p = pages[idx], total = pages.length;
    var label = [p.volume_title, p.label || p.canvas_label || ('Page ' + p.page)].filter(Boolean).join(', ');
    var key = b.id + '#' + idx, saved = isSaved('pages', key);
    bar(b.short || b.title, { back: '#/book/' + b.id, right: '<button class="icon-btn ' + (saved ? 'on' : '') + '" id="savebtn" aria-label="Save page">' + ICON.save + '</button>' });
    document.getElementById('savebtn').onclick = function () {
      var on = toggleSaved('pages', { key: key, book: b.id, idx: idx, title: b.short || b.title, label: label });
      this.classList.toggle('on', on);
    };
    var trc = splitCaveat((p.translation || '').trim()), oc = splitCaveat((p.text || '').trim());
    var tr = trc.text.trim(), orig = oc.text.trim(), caveat = trc.caveat || oc.caveat;
    view.innerHTML = '<img class="rd-img" src="' + esc(p.image) + '" alt="' + esc(label) + '" data-zoom>' +
      '<div class="rd-label"><span>' + esc(label) + '</span><span>' + (idx + 1) + ' of ' + total + '</span></div>' +
      (tr ? '<p class="rd-text">' + esc(tr) + '</p>' + (orig ? '<details class="orig"><summary>Original text' + (p.language ? ' (' + esc(p.language) + ')' : '') + '</summary><div>' + esc(orig) + '</div></details>' : '') +
        (caveat ? '<p class="rd-caveat">' + esc(caveat) + '</p>' : '') +
        '<p class="rd-note">Transcribed and translated by AI from the page image. Read it against the facsimile.</p>'
        : orig ? '<p class="rd-text">' + esc(orig) + '</p>' : '<p class="rd-empty">No text on this page yet. Tap the image to look closer.</p>') +
      '<div class="rd-bar"><button class="btn tonal" id="prev" aria-label="Previous page"' + (idx ? '' : ' disabled') + '>Previous</button>' +
      '<input type="range" min="1" max="' + total + '" value="' + (idx + 1) + '" aria-label="Go to page">' +
      '<button class="btn" id="next" aria-label="Next page"' + (idx < total - 1 ? '' : ' disabled') + '>Next</button></div>';
    window.scrollTo(0, 0);
    function go(i) { location.replace('#/read/' + b.id + '/' + (i + 1)); }
    document.getElementById('prev').onclick = function () { if (idx) go(idx - 1); };
    document.getElementById('next').onclick = function () { if (idx < total - 1) go(idx + 1); };
    var range = view.querySelector('input[type=range]');
    range.onchange = function () { go(parseInt(range.value, 10) - 1); };
    // swipe on the page image to turn pages
    var img = view.querySelector('.rd-img'), sx = 0, sy = 0;
    img.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    img.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) { if (dx < 0 && idx < total - 1) go(idx + 1); if (dx > 0 && idx) go(idx - 1); }
    }, { passive: true });
    // warm the next image
    if (pages[idx + 1]) { var pre = new Image(); pre.src = pages[idx + 1].image; }
  }

  function saved() {
    nav('saved'); bar('Saved');
    var d = store.read();
    if (!d.plants.length && !d.pages.length) {
      view.innerHTML = '<div class="empty"><b>Nothing saved yet</b>Tap the bookmark on a plant or a manuscript page to keep it here.</div>' + foot();
      return;
    }
    view.innerHTML = (d.plants.length ? '<h2 class="sec">Plants</h2><div class="list">' + d.plants.map(function (p) {
      return '<a class="row" href="#/plant/' + esc(p.key) + '"><div class="txt"><div class="nm">' + esc(p.name) + '</div><div class="bot">' + esc(p.botanical || '') + '</div></div></a>';
    }).join('') + '</div>' : '') +
      (d.pages.length ? '<h2 class="sec">Pages</h2><div class="list">' + d.pages.map(function (p) {
        return '<a class="row" href="#/read/' + esc(p.book) + '/' + (p.idx + 1) + '"><div class="txt"><div class="nm">' + esc(p.title) + '</div><div class="dim">' + esc(p.label) + '</div></div></a>';
      }).join('') + '</div>' : '') + foot();
  }

  // ── router ────────────────────────────────────────────────────────────
  function route() {
    var h = location.hash || '#/', path = h.split('?')[0].replace(/^#/, ''), params = qs(h), parts = path.split('/').filter(Boolean);
    if (!lb.hidden) closeLightbox(true);
    if (parts[0] !== 'read') document.body.classList.remove('reading');
    view.focus({ preventScroll: true });
    if (parts[0] !== 'read') window.scrollTo(0, 0);
    if (!parts.length) return searchHome();
    switch (parts[0]) {
      case 'search': return params.q ? searchResults(params) : searchHome();
      case 'plants': return plantList(params);
      case 'plant': return plantDetail(parts[1]);
      case 'library': return library(params);
      case 'book': return bookDetail(parts[1]);
      case 'read':
        if (readerState && readerState.b.id === parts[1] && !params.img) { document.body.classList.add('reading'); return showPage(Math.max(0, Math.min(readerState.pages.length - 1, parseInt(parts[2], 10) - 1))); }
        return reader(parts[1], parts[2], params);
      case 'passage': return passage(params);
      case 'saved': return saved();
      default: return searchHome();
    }
  }
  window.addEventListener('hashchange', route);
  window.addEventListener('popstate', function () { if (!lb.hidden) closeLightbox(true); });

  // links shared from the full site (?plant=MMA-001)
  var sp = new URLSearchParams(location.search);
  if (sp.get('plant') && !location.hash) location.replace('#/plant/' + sp.get('plant'));

  get('/api/m/traditions').then(function (t) { TRAD = t; }).catch(function () {}).then(route);
})();
