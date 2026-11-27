// node scripts/test_prerender_incremental.mjs -- the pieces that let a deploy render only the
// pages that changed. Exits non-zero on the first failure.
import assert from 'node:assert/strict'
import {
  shellKey, shellAssets, relink, spliceLive, legacyLiveSpans, isLiveRead, readValue, readsHash,
  changedPaths, onlyLiveChanged, readProbe,
} from './prerender-incremental.mjs'

const shellA = '<!doctype html><html><head><script type="module" crossorigin src="/assets/index-AAA.js"></script>' +
  '<link rel="stylesheet" crossorigin href="/assets/index-aaa.css"></head><body><div id="root"></div></body></html>'
const shellB = shellA.replace('index-AAA.js', 'index-BBB.js').replace('index-aaa.css', 'index-bbb.css')

// 1. A new bundle is not a new shell; a changed shell is.
assert.equal(shellKey(shellA), shellKey(shellB))
assert.notEqual(shellKey(shellA), shellKey(shellA.replace('<head>', '<head><meta name="x">')))

// 2. Relink points a cached page at the new bundle, and refuses what it cannot map one to one.
const page = shellA.replace('<div id="root"></div>', '<div id="root"><p>hello</p></div>')
const re = relink(page, shellAssets(shellB))
assert.ok(re.includes('/assets/index-BBB.js') && re.includes('/assets/index-bbb.css'))
assert.ok(!re.includes('AAA') && !re.includes('aaa.css'))
assert.equal(relink(page.replace('</head>', '<script src="/assets/index-CCC.js"></script></head>'), shellAssets(shellB)), null)

// 3. Live figures: legacy text is marked, then set to today's value; nothing else moves.
const old = '<p>Data. — full text of 12,293 agendas and sets of minutes, across every town board.</p>' +
  '<div>town documents print the full name, of 11,153 searched</div>' +
  '<p>14 of the 11,153 minutes, agendas and other documents the town published print</p>'
const marked = legacyLiveSpans(old)
assert.equal((marked.match(/data-live=/g) || []).length, 3)
const { html, missing } = spliceLive(marked, k => ({ corpus: '12,314 agendas and sets of minutes', 'named-corpus': '11,174' })[k])
assert.deepEqual(missing, [])
assert.ok(html.includes('full text of <span data-live="corpus">12,314 agendas and sets of minutes</span>, across'))
assert.ok(html.includes('of <span data-live="named-corpus">11,174</span> searched'))
assert.ok(html.includes('14 of the <span data-live="named-corpus">11,174</span> minutes'))
assert.deepEqual(spliceLive(marked, () => undefined).missing.sort(), ['corpus', 'named-corpus'])

// 4. Only a LIVE path changed: the person page's file is unchanged for it; any other change is a change.
const p1 = { name: 'A', named: { count: 3, corpus: 11153, recent: [1] } }
assert.ok(onlyLiveChanged('/data/people/a.json', p1, { ...p1, named: { ...p1.named, corpus: 11174 } }))
assert.ok(!onlyLiveChanged('/data/people/a.json', p1, { ...p1, named: { ...p1.named, corpus: 11174, count: 4 } }))
assert.ok(!onlyLiveChanged('/data/boards.json', p1, { ...p1, named: { ...p1.named, corpus: 11174 } }))
assert.ok(!onlyLiveChanged('/data/people/a.json', p1, p1))   // nothing changed is not "only live"
assert.ok(isLiveRead('/data/people/a.json', 'g["named","corpus"]'))
assert.deepEqual(changedPaths({ a: 1, b: [1, 2] }, { a: 1, b: [1, 3], c: 0 }), [['b', '1'], ['c']])

// 5. The probe, run in node against a fake Response: it records exactly what was read, and
//    readValue recomputes each recorded value from the file.
globalThis.location = { origin: 'http://x' }
globalThis.window = globalThis
globalThis.Response = class { constructor(url, v) { this.url = url; this.v = v } json() { return Promise.resolve(structuredClone(this.v)) } }
readProbe()
const boards = { as_of: '2026-11-23', boards: [{ slug: 'a', n: 1, meetings: [1, 2] }, { slug: 'b', n: 2, meetings: [3] }] }
const data = await new Response('http://x/data/boards.json', boards).json()
const mine = data.boards.find(b => b.slug === 'b')
const shown = [mine.n, mine.meetings.map(m => m * 2), Object.keys(mine)]
assert.deepEqual(shown, [2, [6], ['slug', 'n', 'meetings']])
const rec = window.__pr_reads['/data/boards.json']
assert.equal(rec.whole, false)
for (const [k, v] of Object.entries(rec.r)) assert.equal(readValue(boards, k), v, k)
const keys = Object.keys(rec.r)
const h = readsHash(boards, keys)
// Another board changed, and the date this page never read: same hash -> relinked.
const other = structuredClone(boards); other.boards[0].n = 99; other.as_of = '2026-11-27'
assert.equal(readsHash(other, keys), h)
// Its own board changed: different hash -> rendered.
const own = structuredClone(boards); own.boards[1].meetings.push(4)
assert.notEqual(readsHash(own, keys), h)
// A board inserted before it moves the index it was read at: rendered (safe, not clever).
const ins = structuredClone(boards); ins.boards.unshift({ slug: 'z', n: 0, meetings: [] })
assert.notEqual(readsHash(ins, keys), h)
// A write through the data makes the file whole: the page is keyed on all of it.
const d2 = await new Response('http://x/data/t.json', { xs: [3, 1, 2] }).json()
d2.xs.sort()
assert.equal(window.__pr_reads['/data/t.json'].whole, true)
// Data the page freezes is returned as itself and keys the file whole (a Proxy invariant).
const d3 = await new Response('http://x/data/f.json', { rows: [{ a: 1 }, { a: 2 }] }).json()
const deepFreeze = o => { Object.values(o).forEach(v => typeof v === 'object' && v && deepFreeze(v)); return Object.freeze(o) }
deepFreeze(d3)
assert.equal(d3.rows[0].a, 1)
assert.equal(d3.rows.map(r => r.a).join(), '1,2')
assert.equal(window.__pr_reads['/data/f.json'].whole, true)
// Another origin is not tracked.
await new Response('http://elsewhere/data/x.json', { a: 1 }).json()
assert.equal(window.__pr_reads['/data/x.json'], undefined)

console.log('prerender incremental: all checks passed')
