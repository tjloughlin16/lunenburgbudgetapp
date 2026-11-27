/** WHAT LETS A DEPLOY RENDER ONLY THE PAGES THAT CHANGED. Pure functions, used by
 *  prerender.mjs and tested by test_prerender_incremental.mjs.
 *
 *  TJ, 27 November 2026: *"I only want to deploy the pages that actually changed, with clear
 *  content changes."* Three things made every page re-render on every deploy, and each has
 *  its answer here:
 *
 *  1. THE BUNDLE'S NAME WAS IN EVERY PAGE'S KEY. Any byte of code, or of the data compiled
 *     into the bundle, changed `/assets/index-<hash>.js` and so every page's key. Now the
 *     shell is keyed WITHOUT its asset names (`shellKey`), the bundle is not a dependency,
 *     and a reused page is RELINKED to the new bundle (`relink`). The prerender script's
 *     own text left the key too: `RENDER_FORMAT` in prerender.mjs is bumped by hand when the
 *     shape of the output HTML changes.
 *
 *  2. A FIGURE PRINTED ON EVERY PAGE CHANGED EVERY DAY. The footer names how many meeting
 *     documents the archive holds, and each person's page how many documents were searched
 *     for their name. Both move with every refresh and neither is what the page is about. So
 *     they are LIVE figures: the component marks them `<span data-live="KEY">`, prerender
 *     writes today's value into every page it ships (`spliceLive`), and the JSON path they
 *     come from is not counted as something the page read (`LIVE`).
 *
 *  3. A PAGE READING ONE ENTRY OF A SHARED FILE RE-RENDERED WHEN ANY ENTRY CHANGED. A board
 *     page reads its own board out of boards.json; an edit to another board re-rendered all
 *     288. Now the page records WHICH PARTS of each JSON file it read (`READ_PROBE`, in the
 *     browser) and the cache keeps a hash of those values (`readsHash`). A changed file
 *     re-renders a page only when a value that page read is different.
 *
 *  And a page rendered BEFORE any of this existed has no record of what it read. For those,
 *  the old bytes of each file are kept by hash (`.prerender-cache/blobs`), and a file whose
 *  only change is a LIVE path is not a change to that page (`changedPaths`). Anything else
 *  renders, which is also how the page learns what it reads. */
import { createHash } from 'node:crypto'

const sha256 = s => createHash('sha256').update(s).digest('hex')

/** The shell with its hashed asset names blanked, so a new bundle is not a new shell. */
export function shellKey(shell) {
  return shell.slice(shell.indexOf('<html'))
    .replace(/\/assets\/[A-Za-z0-9_.-]+\.(js|css)/g, '/assets/*.$1')
}

/** The shell's own asset names: what a relinked page must point at. */
export function shellAssets(shell) {
  const js = (shell.match(/<script type="module"[^>]*src="(\/assets\/[^"]+\.js)"/) || [])[1]
  const css = [...shell.matchAll(/<link rel="stylesheet"[^>]*href="(\/assets\/[^"]+\.css)"/g)].map(m => m[1])
  return { js, css }
}

/** A cached page pointed at today's bundle. Refuses (returns null) when the page does not
 *  reference exactly one entry script and as many stylesheets as the shell has, because a
 *  rewrite that cannot be checked one to one is a guess. */
export function relink(html, assets) {
  const js = [...html.matchAll(/\/assets\/index-[A-Za-z0-9_-]+\.js/g)].map(m => m[0])
  if (!assets.js || new Set(js).size !== 1) return null
  let out = html.split(js[0]).join(assets.js)
  const css = [...new Set([...html.matchAll(/<link rel="stylesheet"[^>]*href="(\/assets\/[^"]+\.css)"/g)].map(m => m[1]))]
  if (css.length !== assets.css.length) return null
  css.forEach((c, i) => { out = out.split(c).join(assets.css[i]) })
  return out
}

/** LIVE FIGURES: printed on many pages, changed by every refresh, and not the page's content.
 *  `file` + `path`: where the page reads it (so the read is not counted); `value`: today's
 *  text, exactly as the component formats it. */
export const LIVE = {
  corpus: {
    // Bundled (src/data/agent-manifest.json), so never a fetched read.
    value: ({ manifest }) => (manifest.corpus || '').split(' across ')[0],
  },
  'named-corpus': {
    file: /^\/data\/people\/[^/]+\.json$/, path: ['named', 'corpus'],
    value: ({ json }) => json?.named?.corpus?.toLocaleString('en-US'),
  },
}

const LIVE_SPAN = /<span data-live="([a-z-]+)">([^<]*)<\/span>/g

/** Every live span set to today's value. `values(key)` returns the text, or undefined when
 *  it cannot be known, in which case the result names the key and nothing is written. */
export function spliceLive(html, values) {
  const missing = new Set()
  const out = html.replace(LIVE_SPAN, (m, key) => {
    const v = values(key)
    if (v === undefined || v === null) { missing.add(key); return m }
    return `<span data-live="${key}">${escapeText(String(v))}</span>`
  })
  return { html: out, missing: [...missing] }
}
/** A page cached before the live spans existed prints the same figures as bare text. Mark
 *  them, so the splice can reach them. Each pattern is the component's own sentence, so a
 *  figure is wrapped only where that sentence is. Pages rendered from now on carry the span. */
const LEGACY = [
  ['corpus', /(full text of )([^<]*?)(, across every town board\.)/g],
  ['named-corpus', /(town documents print the full name, of )([\d,]+)( searched)/g],
  ['named-corpus', /(\d+ of the )([\d,]+)( minutes, agendas and other documents the town published)/g],
  ['named-corpus', /(None of the )([\d,]+)( documents the town published prints)/g],
]
export function legacyLiveSpans(html) {
  if (html.includes('data-live="')) return html
  for (const [key, re] of LEGACY) html = html.replace(re, (m, a, v, b) => `${a}<span data-live="${key}">${v}</span>${b}`)
  return html
}
export function liveKeys(html) { return [...new Set([...html.matchAll(LIVE_SPAN)].map(m => m[1]))] }
const escapeText = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** True when a recorded read key is a LIVE path of that file. */
export function isLiveRead(file, key) {
  for (const l of Object.values(LIVE)) {
    if (!l.file || !l.file.test(file)) continue
    if (key === 'g' + JSON.stringify(l.path)) return true
  }
  return false
}

// ---- what a page read out of a JSON file --------------------------------------------------
//
// Keys are an operation and a path: `g["boards","3","slug"]` read that value, `h[...,"x"]`
// asked whether "x" is in it, `k[...]` listed its keys. A value is encoded as `enc` does,
// identically here and in the page, and the write-time check proves they agree.

const enc = v => v === null ? 'null' : Array.isArray(v) ? 'a' : typeof v === 'object' ? 'o'
  : v === undefined ? 'u' : JSON.stringify(v)
const own = (o, k) => o !== null && typeof o === 'object' && Object.prototype.hasOwnProperty.call(o, k)

function walk(root, path) {
  let cur = root
  for (const seg of path) {
    if (!own(cur, seg)) return undefined
    cur = cur[seg]
  }
  return cur
}

/** The value a read key has in `root`, encoded as the page encoded it. */
export function readValue(root, key) {
  const op = key[0]
  const path = JSON.parse(key.slice(1))
  if (op === 'g') {
    if (!path.length) return enc(root)
    const parent = walk(root, path.slice(0, -1))
    return own(parent, path[path.length - 1]) ? enc(parent[path[path.length - 1]]) : 'u'
  }
  if (op === 'h') {
    const parent = walk(root, path.slice(0, -1))
    return String(parent !== null && typeof parent === 'object' && path[path.length - 1] in parent)
  }
  if (op === 'k') {
    const o = walk(root, path)
    return o !== null && typeof o === 'object' ? JSON.stringify(Reflect.ownKeys(o)) : 'u'
  }
  throw new Error(`unknown read key ${key}`)
}

/** One hash for the values a page read. Keys sorted, so the order of reading is irrelevant. */
export function readsHash(root, keys) {
  return sha256(JSON.stringify([...keys].sort().map(k => [k, readValue(root, k)])))
}

/** The JSON paths at which two parsed values differ, as arrays; capped, because past the cap
 *  the answer is only ever used to say "more than the live paths". */
export function changedPaths(a, b, cap = 50) {
  const out = []
  const go = (x, y, p) => {
    if (out.length >= cap) return
    const tx = Array.isArray(x) ? 'a' : typeof x, ty = Array.isArray(y) ? 'a' : typeof y
    if (tx !== ty || x === null || y === null || tx !== 'object' && tx !== 'a') {
      if (x !== y) out.push(p)
      return
    }
    for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) {
      if (!(k in x) || !(k in y)) { out.push([...p, k]); if (out.length >= cap) return }
      else go(x[k], y[k], [...p, k])
    }
  }
  go(a, b, [])
  return out
}

/** True when every difference between the two versions of `file` is a LIVE path of it. */
export function onlyLiveChanged(file, before, after) {
  const live = Object.values(LIVE).filter(l => l.file && l.file.test(file)).map(l => JSON.stringify(l.path))
  if (!live.length) return false
  const d = changedPaths(before, after)
  return d.length > 0 && d.every(p => live.includes(JSON.stringify(p)))
}

/** THE PAGE'S HALF: injected into the served shell beside the clock probe. Wraps
 *  Response.prototype.json for same-origin files so each parsed value is a Proxy that
 *  records what was read, in `window.__pr_reads[path] = {r: {key: value}, whole}`. A
 *  write, a delete, or more than LIMIT distinct reads makes the file `whole`: the page is
 *  then keyed on the whole file, exactly as before. Written as a function so it can be
 *  stringified into the page and tested in node. */
export function readProbe() {
  var LIMIT = 20000
  var reads = (window.__pr_reads = {})
  var enc = function (v) {
    return v === null ? 'null' : Array.isArray(v) ? 'a' : typeof v === 'object' ? 'o'
      : v === undefined ? 'u' : JSON.stringify(v)
  }
  var J = Response.prototype.json
  Response.prototype.json = function () {
    var file = null
    try { var u = new URL(this.url); if (u.origin === location.origin) file = u.pathname } catch (e) { /* no url */ }
    var p = J.apply(this, arguments)
    return file ? p.then(function (v) { return track(v, file) }) : p
  }
  function track(root, file) {
    var rec = reads[file] || (reads[file] = { r: {}, n: 0, whole: false })
    var proxies = new WeakMap()
    function note(k, v) {
      if (rec.whole || Object.prototype.hasOwnProperty.call(rec.r, k)) return
      if (++rec.n > LIMIT) { rec.whole = true; rec.r = {}; return }
      rec.r[k] = v
    }
    function spoil() { rec.whole = true; rec.r = {} }
    function wrap(v, path) {
      if (v === null || typeof v !== 'object') return v
      var p = proxies.get(v)
      if (p) return p
      p = new Proxy(v, {
        get: function (t, k, r) {
          if (typeof k === 'symbol') return Reflect.get(t, k, r)
          if (Object.prototype.hasOwnProperty.call(t, k)) {
            var x = t[k]
            note('g' + JSON.stringify(path.concat([k])), enc(x))
            return wrap(x, path.concat([k]))
          }
          if (!(k in t)) note('g' + JSON.stringify(path.concat([k])), 'u')
          return Reflect.get(t, k, r)
        },
        has: function (t, k) {
          if (typeof k !== 'symbol') note('h' + JSON.stringify(path.concat([k])), String(k in t))
          return k in t
        },
        ownKeys: function (t) {
          var ks = Reflect.ownKeys(t)
          note('k' + JSON.stringify(path), JSON.stringify(ks))
          return ks
        },
        getOwnPropertyDescriptor: function (t, k) {
          var d = Reflect.getOwnPropertyDescriptor(t, k)
          if (d && typeof k !== 'symbol') note('g' + JSON.stringify(path.concat([k])), enc(d.value))
          return d
        },
        set: function (t, k, v) { spoil(); t[k] = v; return true },
        deleteProperty: function (t, k) { spoil(); return delete t[k] },
        defineProperty: function (t, k, d) { spoil(); return Reflect.defineProperty(t, k, d) },
      })
      proxies.set(v, p)
      return p
    }
    note('g[]', enc(root))
    return wrap(root, [])
  }
}
export const READ_PROBE = `<script id="__prerender_reads">(${readProbe.toString()})()</script>`
export const READ_PROBE_RE = /<script id="__prerender_reads">[\s\S]*?<\/script>/
