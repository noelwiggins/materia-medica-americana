// Export the BOOKS registry from index.html to static/data/books.json (read by the mobile app and its API).
// Run after editing BOOKS in index.html:  node scripts/export_books.js
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const s = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const i = s.indexOf('const BOOKS = [');
const j = s.indexOf('\n];', i);
const BOOKS = eval(s.slice(i + 'const BOOKS = '.length, j + 2));
const seen = new Set(), out = [];
for (const b of BOOKS) { if (!b || seen.has(b.id)) continue; seen.add(b.id); out.push(b); }
fs.writeFileSync(path.join(root, 'static/data/books.json'), JSON.stringify({ books: out }, null, 1));
console.log('exported', out.length, 'books');
