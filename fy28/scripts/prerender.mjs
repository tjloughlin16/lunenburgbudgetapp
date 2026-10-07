/**
 * Write real HTML into the build, one file per route.
 *
 * The app is client-side rendered: `index.html` ships `<div id="root"></div>` and nothing
 * else, and `_redirects` resolves every path to that same file. So every URL on the site
 * returned a byte-identical 6,122-byte shell, and anything that reads HTML without running
 * JavaScript — an assistant asked to check a figure, a search crawler, a link preview — got
 * an empty div. For a site whose whole argument is "check this yourself", that is the
 * argument failing at the door.
 *
 * This renders each route in headless Chrome and writes the resulting DOM to
 * `dist/<slug>.html`, which Cloudflare Pages serves in preference to the SPA fallback. The page a reader sees is unchanged; the page a fetcher sees is now the page.
 *
 * Three things make this cheap and low-risk here, and they are worth knowing before
 * changing any of them:
 *
 *   1. `main.tsx` uses `createRoot`, not `hydrateRoot`. React discards whatever is in
 *      `#root` and renders from scratch. So the prerendered markup carries NO hydration
 *      contract — it cannot desynchronise from the app, and a stale snapshot degrades to
 *      "a reader without JS sees slightly old prose", never to a broken page.
 *   2. Chrome is driven through its own `--dump-dom`, so there is no Puppeteer, no bundled
 *      Chromium download, and nothing added to package.json.
 *   3. Routes come from `src/routes.ts`, the table the app itself routes on, so a page
 *      added there cannot be silently missed here.
 *
 * What this does NOT do, and should not be described as doing: the interactive pages
 * snapshot at their DEFAULT state. Every dial is where it opens. That is the right floor
 * for a reader and for an agent — the prose and the settled figures — and it is not the
 * app. Do not let a prerendered number be quoted as though somebody had set the dials.
 *
 *     node scripts/prerender.mjs          # after `npm run build`
 *
 * Exits non-zero if any route renders empty, if a route is missing from sitemap.xml, or if
 * a rendered page lost its module script (which would mean shipping a dead page).
 */
import { createServer } from 'node:http'
import { execFile } from 'node:child_process'
import { readFile, writeFile, mkdir, readdir, stat, rm, rename } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { promisify } from 'node:util'
import { join, extname, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const execFileAsync = promisify(execFile)
const HERE = dirname(fileURLToPath(import.meta.url))
const APP = join(HERE, '..')
const DIST = join(APP, 'dist')
const ROUTES_TS = join(APP, 'src', 'routes.ts')
const SITEMAP = join(APP, 'public', 'sitemap.xml')
// Read, not typed. `agent-manifest.json` already holds the one copy of this host that the
// app's own absolute links are built from, and a second literal here is a latent drift.
const SITE = JSON.parse(
  await readFile(join(APP, 'src', 'data', 'agent-manifest.json'), 'utf8')).site
// NO FIXED PORT. This was 8794, and a fixed port is machine-wide while a worktree is not:
// the nightly refresh builds from ~/lunenburgbudgets-refresh at the same moment somebody
// builds from the main checkout, and the second one dies with EADDRINUSE. That is not a
// theoretical race -- it is why the refresh failed on 20 September 2026, and the standing
// advice to "check the port before building" cannot fix it, because check-then-bind is
// itself a race.
//
// Port 0 asks the OS for a free one, so two builds can never collide. The real port is
// read back off the server once it is listening, below.

// A page that renders to less than this much visible text has not rendered. The smallest
// real page on the site is several times this; the empty shell is zero.
const MIN_TEXT = 2000

const CHROME_CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean)

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.csv': 'text/csv', '.svg': 'image/svg+xml',
  '.xml': 'application/xml', '.txt': 'text/plain; charset=utf-8', '.pdf': 'application/pdf',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.md': 'text/markdown',
}

/** The routes the app actually routes on, read from its own table.
 *
 *  Parsed rather than imported because this is a .ts file with type annotations and we are
 *  running plain node. The parse is asserted against the `Tab` union in the same file, so a
 *  route added to one and not the other fails here rather than going unrendered. */
async function readRoutes() {
  const src = await readFile(ROUTES_TS, 'utf8')

  const block = src.match(/export const SLUG: Record<Tab, string> = \{([\s\S]*?)\n\}/)
  if (!block) throw new Error('routes.ts: could not find the SLUG table')
  const slugs = [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)].map(m => m[2])

  const union = src.match(/export type Tab =([\s\S]*?)\n\n/)
  if (!union) throw new Error('routes.ts: could not find the Tab union')
  const tabs = [...union[1].matchAll(/'([a-z]+)'/g)].map(m => m[1])

  if (slugs.length !== tabs.length) {
    throw new Error(`routes.ts: ${tabs.length} tabs in the union but ${slugs.length} in ` +
      'SLUG. One of them has a route the other does not, and this script renders SLUG.')
  }
  // Unlisted routes are deliberately excluded from the render.
  //
  // They are in no sitemap, so the sitemap assertion below would fail on them, and a
  // prerendered file is exactly what an unlisted page should not leave lying in dist for
  // a directory listing or a crawler that guesses. The page still WORKS -- the SPA
  // fallback serves index.html for any path and React routes it -- it simply has no
  // static twin. A reader without JavaScript does not get it, which for a working page
  // handed to named people is the right trade.
  const unlisted = new Set(
    [...(src.match(/export const UNLISTED[^\n]*\n/) ?? [''])[0]
      .matchAll(/'([a-z]+)'/g)].map(m => m[1]))
  const bySlug = [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)]
  const listed = bySlug.filter(m => !unlisted.has(m[1])).map(m => m[2])
  if (unlisted.size) {
    console.log(`  skipping ${unlisted.size} unlisted route(s): ` +
      bySlug.filter(m => unlisted.has(m[1])).map(m => `/${m[2]}`).join(', '))
  }

  const routes = listed.map(s => (s ? `/${s}` : '/'))

  // THE MARKDOWN ANALYSES, one route each.
  //
  // They share a single Tab -- the document id is the second path segment -- so SLUG
  // holds one entry for all of them and enumerating from it would render one page.
  // Read off the published documents instead, which is the same discipline the rest of
  // this script follows: the routes come from the thing that decides them, never from a
  // list kept beside it. A document added to public/docs/analyses is prerendered the
  // same day, and `build_reports_index.py --check` fails if it is missing from /reports.
  //
  // MINUS THE UNLISTED ONES, for the same reason an unlisted Tab gets no static twin: a
  // prerendered file is what an unlisted page should not leave in dist for a crawler that
  // guesses, and the route is absent from sitemap.xml so the assertion below would fail on
  // it anyway. The declared set is sources/analyses/UNLISTED, read here and by
  // build_sitemap.py and build_reports_index.py, so one file decides it.
  const hiddenDocs = new Set(
    (existsSync(join(APP, '..', 'sources', 'analyses', 'UNLISTED'))
      ? (await readFile(join(APP, '..', 'sources', 'analyses', 'UNLISTED'), 'utf8')).split('\n')
      : []).map(l => l.split('#')[0].trim()).filter(Boolean))
  const docs = (await readdir(join(APP, 'public', 'docs', 'analyses')))
    .filter(f => f.endsWith('.md')).map(f => f.slice(0, -3))
    .filter(d => !hiddenDocs.has(d)).sort()
  if (!docs.length) throw new Error('no analyses in public/docs/analyses — nothing to render')
  if (hiddenDocs.size) console.log(`  ${hiddenDocs.size} unlisted analysis(es) not rendered: ${[...hiddenDocs].join(', ')}`)
  console.log(`  ${docs.length} markdown analyses at /analysis/<id>`)

  // THE BLOG POSTS THAT HAVE BEEN PUBLISHED, and only those.
  //
  // Same shape as the analyses -- one Tab, the slug in the second path segment -- and the
  // same discipline: the routes come from the thing that decides them. What is different
  // is that a post has a STATE. A draft (no publication date) or a scheduled one (a date
  // in the future) is reachable by its link and listed nowhere, so it gets no static twin,
  // no sitemap entry and no place in dist for a crawler to find. Prerendering one would be
  // publishing it, which is the one decision in this pipeline that belongs to a person.
  const blogFile = join(APP, 'public', 'data', 'blog.json')
  let posts = []
  if (existsSync(blogFile)) {
    const today = new Date().toISOString().slice(0, 10)
    posts = JSON.parse(await readFile(blogFile, 'utf8')).posts
      .filter(p => p.publish && p.publish <= today).map(p => p.slug).sort()
    console.log(`  ${posts.length} published blog posts at /blog/<slug>`)
  }
  // ONE PAGE PER BOARD. Client-rendered from boards.json until 17 September 2026, which
  // meant a feed reader (or a search engine) fetching /boards/school-committee got the
  // app shell: no title, no <link rel="alternate"> to the board's feed. The list comes
  // from the payload, as the blog's comes from blog.json.
  const boardsFile = join(APP, 'public', 'data', 'boards.json')
  let boards = [], finance = []
  if (existsSync(boardsFile)) {
    const all = JSON.parse(await readFile(boardsFile, 'utf8')).boards
    boards = all.map(b => b.slug).sort()
    console.log(`  ${boards.length} boards at /boards/<slug>`)
    // THE FINANCE TAB of every board that owns an account; the School Committee's is a
    // top-level route already (routes.ts: schoolfinance).
    finance = all.filter(b => b.finance && b.slug !== 'school-committee').map(b => `/boards/${b.slug}/finance`).sort()
    console.log(`  ${finance.length} board finance pages at /boards/<slug>/finance`)
  }
  // THE RECORDS TAB, for every board the meeting register resolves a slug for --
  // build_board_records.py drops the rows with no resolved board_slug at all.
  const recordsFile = join(APP, 'public', 'data', 'board-records.json')
  let records = []
  if (existsSync(recordsFile)) {
    const recs = JSON.parse(await readFile(recordsFile, 'utf8')).boards
    records = recs.map(b => `/boards/${b.board_slug}/records`).sort()
    console.log(`  ${records.length} board records pages at /boards/<slug>/records`)
  }
  // EVERY MEETING WITH OUR MINUTES. Client-rendered until 17 September 2026, so a link
  // shared on Facebook carried the site's description rather than the meeting's headline.
  const minutesFile = join(APP, 'public', 'data', 'recording-minutes.json')
  let meetings = []
  if (existsSync(minutesFile)) {
    meetings = JSON.parse(await readFile(minutesFile, 'utf8')).meetings.map(m => `/meeting-minutes/${m.slug}`).sort()
    console.log(`  ${meetings.length} meetings at /meeting-minutes/<board>/<date>-<video>`)
  }
  const financeFile = join(APP, 'public', 'data', 'finance.json')
  let departments = []
  if (existsSync(financeFile)) {
    const f = JSON.parse(await readFile(financeFile, 'utf8'))
    departments = f.departments.filter(x => f.owners[x.slug]).map(x => `/departments/${x.slug}`).sort()
    console.log(`  ${departments.length} departments at /departments/<slug>`)
  }
  return [...routes, ...docs.map(d => `/analysis/${d}`), ...posts.map(s => `/blog/${s}`), ...boards.map(s => `/boards/${s}`), ...finance, ...records, ...departments, ...meetings]
}

/** Serve dist, falling back to the PRISTINE shell -- with the probe in it.
 *
 *  Pristine matters: this script overwrites dist/index.html with the rendered root. Without
 *  holding the original in memory, a second run would prerender a page that was already
 *  prerendered, nesting the output. Serving from memory makes the script idempotent.
 *
 *  ONE SERVER PER WORKER, and each records every path requested of it. A worker renders one
 *  route at a time, so everything its server saw between two renders is what that route
 *  READ -- an observed dependency list, never a hand-kept one. Several Chrome processes
 *  sharing one server could not be told apart. */
function serve(shell) {
  const probed = shell.replace('<script type="module"', `${PROBE}<script type="module"`)
  const seen = new Set()
  const server = createServer(async (req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname)
    seen.add(path)
    const file = join(DIST, path)
    try {
      const s = await stat(file)
      if (s.isFile()) {
        res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
        res.end(await readFile(file))
        return
      }
    } catch { /* falls through to the shell, exactly as the host does */ }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
    res.end(probed)
  })
  server.seen = seen
  return server
}

/** WHAT A PAGE READS THAT IS NOT A FILE: THE CLOCK, AND OTHER HOSTS.
 *
 *  A route's HTML is a function of the files it fetched -- which the server sees -- and of
 *  two things it cannot see. "Upcoming meetings" and "in 3 days" read today's date, so a
 *  board page rendered yesterday is wrong today with every input file unchanged. And a
 *  fetch to another origin never reaches our server at all.
 *
 *  So the served shell carries this probe. It wraps fetch, so that a cross-origin request
 *  marks the document, and it wraps Date -- carefully, because CREATING a date is not
 *  READING the clock. d3-time makes two blank `new Date` objects as scratch space when it
 *  loads and overwrites them before use; Cloudflare's beacon reads the time for its own
 *  timing. The first version of this probe counted both, flagged every one of 830 routes as
 *  date-dependent and would have reused nothing past midnight. So:
 *
 *    - `Date.now()` is a read.
 *    - A bare `new Date()` is a read only if its VALUE is used -- any getter, formatter,
 *      arithmetic, or copying it into another Date or an Intl format -- before a setter
 *      has overwritten it.
 *    - A read whose caller is another origin's script is not counted: it cannot reach the
 *      DOM except through our own code, which would be counted itself.
 *
 *  The marks come back in the dumped DOM and are stripped, with the probe, before anything
 *  is written. A page that reads the clock is reused only on the same calendar day; one
 *  that reads another host is never reused. A false positive costs one re-render; the
 *  probe exists so that there is no false negative to cost a stale page. */
const PROBE = `<script id="__prerender_probe">(function(){` +
  `var R=document.documentElement,D=Date,O=location.origin,DOC=location.href.split('#')[0],NOW=Symbol(),DP=D.prototype;` +
  `function mark(k){R.setAttribute('data-pr-'+k,'1')}` +
  // The caller is the first frame that is a script and is not this probe (inline, so its
  // frames carry the document's own URL).
  `function clock(){var L=(new Error().stack||'').split('\\n').slice(1);for(var i=0;i<L.length;i++){` +
  `var c=L[i];if(c.indexOf('http')<0||c.indexOf(DOC+':')>=0)continue;if(c.indexOf(O)>=0)mark('clock');return}}` +
  `function use(d){if(d&&d[NOW])clock()}` +
  `class P extends D{constructor(...a){use(a[0]);super(...a);if(!a.length)this[NOW]=1}}` +
  `P.now=function(){clock();return D.now()};` +
  `Object.getOwnPropertyNames(DP).forEach(function(k){var f=DP[k];` +
  `if(k==='constructor'||typeof f!=='function')return;` +
  `P.prototype[k]=k.slice(0,3)==='set'?function(){this[NOW]=0;return f.apply(this,arguments)}` +
  `:function(){use(this);return f.apply(this,arguments)}});` +
  `var TP=DP[Symbol.toPrimitive];P.prototype[Symbol.toPrimitive]=function(h){use(this);return TP.call(this,h)};` +
  `window.Date=P;` +
  `var IP=Intl.DateTimeFormat.prototype;['format','formatToParts','formatRange','formatRangeToParts'].forEach(function(k){` +
  `var g=Object.getOwnPropertyDescriptor(IP,k);if(!g)return;var get=g.get,val=g.value;` +
  `function wrap(f){return function(){if(!arguments.length)clock();for(var i=0;i<arguments.length;i++)use(arguments[i]);return f.apply(this,arguments)}}` +
  `if(get)Object.defineProperty(IP,k,{configurable:true,get:function(){return wrap(get.call(this))}});` +
  `else Object.defineProperty(IP,k,{configurable:true,writable:true,value:wrap(val)})});` +
  `var F=window.fetch;window.fetch=function(i){try{var u=new URL(typeof i==='string'?i:i.url,location.href);` +
  `if(u.origin!==O)mark('external')}catch(e){}return F.apply(this,arguments)}` +
  `})()</script>`
const PROBE_RE = /<script id="__prerender_probe">[\s\S]*?<\/script>/
const MARK_RE = / data-pr-(clock|external)="1"/g

/** Visible text, the way a reader without JS would experience the page. */
function visibleText(html) {
  const body = html.slice(Math.max(0, html.indexOf('<div id="root"')))
  return body
    .replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;|&#\d+;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** REUSE A PAGE ONLY WHEN EVERY INPUT IT WAS SEEN TO READ IS BYTE-IDENTICAL.
 *
 *  TJ, 7 October 2026: *"we should only be regenerating the pages that have changed."* A
 *  full render was 36.5 minutes for 781 routes, and most builds change a handful of data
 *  files. The cache lives OUTSIDE dist/ because `vite build` empties dist/ every time.
 *
 *  An entry is reused when: the shell, this script and the probe are unchanged (GLOBAL);
 *  every path the route requested last time hashes the same now -- the JS and CSS bundle
 *  among them, so any code change re-renders every page; the page did not read another
 *  host; and if it read the clock, it was rendered today. Anything else renders: a route
 *  never seen, a route with no entry, a cached file gone missing. FULL=1 renders all of
 *  them, for when the map itself is in doubt. */
const CACHE = join(APP, '.prerender-cache')
const CACHE_HTML = join(CACHE, 'html')
const CACHE_DEPS = join(CACHE, 'deps.json')
const JOBS = Math.max(1, Number(process.env.PRERENDER_JOBS) || 4)
const sha256 = buf => createHash('sha256').update(buf).digest('hex')
const cachedFile = route => join(CACHE_HTML, `${encodeURIComponent(route)}.html`)
const today = () => new Date().toLocaleDateString('en-CA')

const hashes = new Map()
/** The sha256 of what dist/ would serve for a path, or `shell` for the fallback. Memoised:
 *  a data file hashed once per run, however many routes read it. */
async function hashOf(path) {
  if (!hashes.has(path)) {
    hashes.set(path, (async () => {
      try {
        const file = join(DIST, path)
        if ((await stat(file)).isFile()) return sha256(await readFile(file))
      } catch { /* not a file: the host answers with the shell */ }
      return 'shell'
    })())
  }
  return hashes.get(path)
}

async function canReuse(entry, route, global) {
  if (!entry || entry.global !== global || entry.external) return false
  if (entry.clock && entry.date !== today()) return false
  // The page itself, against the hash recorded beside it: a run killed after writing a page
  // and before writing the map leaves a newer page under an older entry.
  if (!existsSync(cachedFile(route)) || sha256(await readFile(cachedFile(route))) !== entry.html) return false
  for (const [path, h] of Object.entries(entry.deps)) {
    if (await hashOf(path) !== h) return false
  }
  return true
}

async function main() {
  if (!existsSync(DIST)) {
    console.error('no dist/ — run `npm run build` first')
    process.exit(1)
  }
  const chrome = CHROME_CANDIDATES.find(p => existsSync(p))
  if (!chrome) {
    console.error('no Chrome found. Set CHROME=/path/to/chrome. Looked in:\n  ' +
      CHROME_CANDIDATES.join('\n  '))
    process.exit(1)
  }

  const all = await readRoutes()

  // ONLY=/a/route,/another — prerender just these, leaving every other file in dist
  // alone. Two jobs, and the second is the one that matters:
  //
  //   RETRY ONE ROUTE. Chrome fails on a single page occasionally and non-repeatably.
  //   Without this the only remedy is a full rebuild — 381 routes, fifteen minutes — to
  //   recover one file, so the tempting alternative is deploying with that page's
  //   prerendered HTML missing, which silently drops it back to client-side only. That
  //   costs exactly the readers the prerender exists for: the agents that cannot run
  //   JavaScript, and the ones whose fetcher only accepts indexed URLs.
  //
  //   AND IT IS THE SHAPE THE DAILY REFRESH NEEDS. One page's Chrome death has taken
  //   down a whole refresh run more than once. A retry pass over the failures is only
  //   possible if a route can be rendered on its own.
  //
  // The shell check below still applies: this reads dist/index.html for the preamble, so
  // ONLY cannot be used against a dist that has already been prerendered over.
  //
  // ONLY never reuses: naming a route is asking for it to be rendered.
  const only = (process.env.ONLY || '').split(',').map(s => s.trim()).filter(Boolean)
  const routes = only.length ? all.filter(r => only.includes(r)) : all
  if (only.length) {
    const missing = only.filter(r => !all.includes(r))
    if (missing.length) {
      console.error(`ONLY names routes this build does not have: ${missing.join(', ')}`)
      process.exit(1)
    }
    console.log(`ONLY: ${routes.length} of ${all.length} routes`)
  }
  const shell = await readFile(join(DIST, 'index.html'), 'utf8')

  // This script overwrites dist/index.html, so on a second run without an intervening
  // build the "shell" read here is already a prerendered page. That is not harmless: the
  // pre-<html> preamble is taken from it, and a prerendered file has already lost it, so
  // the agent comment would be silently dropped from every page from then on. It was, for
  // exactly one run. Refuse instead.
  if (!/<div id="root">\s*<\/div>/.test(shell)) {
    console.error('dist/index.html is already prerendered — #root is not empty.\n' +
      'Run `npm run build` first; prerendering a prerender loses the agent comment.')
    process.exit(1)
  }

  // The module script is what boots React. If a render loses it we would be shipping a
  // page that looks right and does nothing, which is worse than the empty shell.
  const scriptTag = shell.match(/<script type="module"[^>]*src="([^"]+)"/)
  if (!scriptTag) throw new Error('dist/index.html has no module script; is this a real build?')

  // Everything before <html>: the doctype and the note addressed to assistants reading
  // the page. Chrome's --dump-dom serialises the DOM from the document element down and
  // silently drops both, so a prerendered page would lose the one piece of the file that
  // is written TO the audience this whole exercise is for. Spliced back verbatim.
  const preamble = shell.slice(0, shell.indexOf('<html'))
  if (!preamble.includes('<!doctype') && !preamble.includes('<!DOCTYPE')) {
    throw new Error('index.html: no doctype found before <html>')
  }

  const sitemap = await readFile(SITEMAP, 'utf8')

  // DECIDE WHAT TO REUSE before any Chrome starts, and say so.
  const global = sha256(shell + PROBE + await readFile(fileURLToPath(import.meta.url), 'utf8'))
  let deps = {}
  try { deps = JSON.parse(await readFile(CACHE_DEPS, 'utf8')) } catch { /* first run */ }
  const full = !!process.env.FULL || only.length > 0
  const reuse = [], render = []
  for (const route of routes) {
    if (!full && await canReuse(deps[route], route, global)) reuse.push(route)
    else render.push(route)
  }
  console.log(`${render.length} to render, ${reuse.length} reused (every input unchanged)` +
    (process.env.FULL ? ' — FULL=1' : '') + `, ${JOBS} at a time`)

  const servers = Array.from({ length: Math.min(JOBS, Math.max(render.length, 1)) }, () => serve(shell))
  for (const s of servers) await new Promise(r => s.listen(0, r))
  // PREFLIGHT, BECAUSE ENOSPC DOES NOT PRESENT AS A DISK PROBLEM. When the disk filled on
  // 19 September 2026 the visible symptom was a prerender exiting 1 with no message, then
  // every unrelated command failing too. Fail here, with the reason, rather than there.
  await assertSpace()
  // And sweep what earlier builds leaked, so a machine that already has the problem heals
  // itself rather than needing somebody to know about it. Only what is a day old: a
  // concurrent build's profile is not ours to delete.
  await sweepLeakedProfiles()

  console.log(`prerendering ${render.length} routes with ${chrome}\n`)

  // WHAT CHROME LEAVES BEHIND, AND WHY WE NO LONGER TOUCH HOW IT MAKES IT.
  //
  // With no --user-data-dir Chrome mints its own profile under
  // ~/Library/Caches/Google/Chrome-headless per launch, and never removes it. This loop
  // launches once per route, so a build left ~332 behind; by 19 September 2026 there were
  // 35,206 holding 128 GB and the disk hit 572 MB free, which does not present as "the
  // cache is full" but as every build, script and tool failing with ENOSPC at once.
  //
  // THE FIRST FIX WAS WORSE THAN THE BUG. Passing our own --user-data-dir made Chrome run
  // full first-run profile initialisation on every launch: the render went from seconds a
  // route to hitting the 300s timeout on EVERY route -- 12 pages in 64 minutes. Chrome's
  // own scoped dir is fast and was never the problem. The problem was only that nothing
  // ever deleted it.
  //
  // So: leave Chrome's behaviour exactly as it was, note the time we started, and sweep
  // what this run created once it is done. Add the teardown, do not replace the mechanism.
  const startedAt = Date.now()

  const failures = []
  const rows = []
  await mkdir(CACHE_HTML, { recursive: true })

  /** The checks every page passes, rendered or reused. Returns the reason it fails. */
  function check(route, html, text) {
    if (text.length < MIN_TEXT) return `${route}: rendered only ${text.length} chars of text (min ${MIN_TEXT})`
    if (!html.includes(scriptTag[1])) return `${route}: rendered HTML lost the module script ${scriptTag[1]}`
    if (!html.startsWith(preamble)) return `${route}: lost the doctype/agent-comment preamble`
    if (PROBE_RE.test(html) || /data-pr-(clock|external)/.test(html)) return `${route}: the prerender probe leaked into the page`
    // THE BUILD SERVER'S ADDRESS, written into a page that ships. Every one of 830 pages
    // carried og:url=http://localhost:61348/... until 7 October 2026, read off
    // window.location.origin at render time. Use SITE from src/lib/abs.ts.
    if (/https?:\/\/(localhost|127\.0\.0\.1):\d+/.test(html)) return `${route}: carries the prerender server's own address (localhost) -- build URLs from SITE in src/lib/abs.ts`
    return null
  }

  async function write(route, html, text) {
    if (route !== '/' && !sitemap.includes(`<loc>https://lunenburgbudgetproject.org${route}</loc>`)) {
      failures.push(`${route}: rendered fine but is missing from public/sitemap.xml`)
    }
    // `<slug>.html`, NOT `<slug>/index.html`. Pages serves a directory by 308-redirecting
    // /athletics to /athletics/, so the canonical URL in the sitemap would answer with a
    // redirect rather than the page -- an extra hop, and one some fetchers do not follow.
    // Extension-less serving of <slug>.html answers /athletics directly with 200.
    const out = route === '/' ? join(DIST, 'index.html') : join(DIST, `${route}.html`)
    await mkdir(dirname(out), { recursive: true })
    await writeFile(out, html)
    rows.push({ route, bytes: html.length, text: text.length, text_body: text })
  }

  // THE REUSED PAGES go through every check a rendered one does. A cached file is not
  // trusted for being cached.
  for (const route of reuse) {
    const html = await readFile(cachedFile(route), 'utf8')
    const text = visibleText(html)
    const bad = check(route, html, text) || (html.includes(`<link rel="canonical" href="${SITE}${route}">`)
      ? null : `${route}: cached page has no canonical link`)
    if (bad) { failures.push(bad); delete deps[route]; continue }
    await write(route, html, text)
  }

  let done = 0
  const t0 = Date.now()
  async function renderOne(route, server) {
    const url = `http://localhost:${server.address().port}${route}`
    let html
    // RETRY ONCE, BECAUSE THIS FAILURE IS NOT ABOUT THE PAGE.
    //
    // Chrome dies on a single route occasionally and non-repeatably — /boards/board-of-assessors
    // failed one run and renders fine on the live site from the identical code. Before
    // this, one such death cost the route its prerendered HTML for the whole build, and
    // the only remedy was another fifteen-minute run. The tempting alternative was
    // shipping without it, which silently drops that page to client-side only and costs
    // exactly the readers the prerender exists for.
    //
    // It has also taken down whole daily refreshes. A second attempt is cheap — one
    // page, seconds — and a route that fails TWICE is a real failure and still reported,
    // so this buys tolerance of a flake without hiding a break.
    let lastErr = null
    for (let attempt = 0; attempt < 2 && html === undefined; attempt++) {
      server.seen.clear()
      try {
        const { stdout } = await execFileAsync(chrome, [
          '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
          // React and recharts settle on timers; virtual time lets Chrome run them to
          // completion immediately rather than us guessing at a sleep.
          '--virtual-time-budget=10000',
          '--run-all-compositor-stages-before-draw',
          '--dump-dom', url,
        ], {
          maxBuffer: 64 * 1024 * 1024,
          // A HANG MUST FAIL, NOT WAIT. With no timeout a wedged Chrome is awaited for
          // ever: one sat rendering a single route for two and a half days, holding its
          // profile open, while the build that started it was long gone. Five minutes is
          // deliberately loose -- this is here to catch a WEDGE, not to police a slow page,
          // and 90s was tight enough to fail every transcript page on the site.
          timeout: 300_000,
          killSignal: 'SIGKILL',
        })
        html = preamble + stdout.slice(stdout.indexOf('<html'))
      } catch (e) {
        lastErr = e
        if (attempt === 0) console.log(`  retrying ${route} — chrome failed once`)
      }
    }
    delete deps[route]
    if (html === undefined) {
      // LOG WHAT NODE ACTUALLY ATTACHED, not `.message`. Its first line is only ever
      // "Command failed: <the command we already know>", so every Chrome failure in this
      // loop read identically: a hang killed by our own timeout, a renderer crash and a
      // real page bug all produced the same one-line entry with the actual reason thrown
      // away. That cost three separate triage sessions on 20-21 September, each of which
      // reached "transient Chrome crash, could not confirm" because the evidence had
      // already been discarded at the point of failure.
      //
      // This block is the refresh triage agent's, adopted from the fix it wrote in the
      // refresh worktree and could not commit. It is better than the version that was
      // here and it is kept in its own words.
      const detail = [
        lastErr.signal ? `signal ${lastErr.signal}` : null,
        Number.isInteger(lastErr.code) ? `exit ${lastErr.code}` : null,
        (lastErr.stderr || '').trim().split('\n').filter(Boolean).slice(0, 2).join(' / '),
      ].filter(Boolean).join(', ')
      failures.push(`${route}: chrome failed twice` +
        (detail ? ` — ${detail}` : ' — no signal, code or stderr on the error'))
      return
    }

    // What the page read, before the probe's marks are stripped.
    const clock = /<html[^>]* data-pr-clock="1"/.test(html)
    const external = /<html[^>]* data-pr-external="1"/.test(html)
    const read = [...server.seen].sort()
    html = html.replace(PROBE_RE, '').replace(MARK_RE, '')

    const text = visibleText(html)
    const bad = check(route, html, text)
    if (bad) { failures.push(bad); return }

    // A SELF-REFERENTIAL canonical, one per route, injected here rather than put in
    // index.html — the template is shared by every route, so a canonical in it would
    // name the homepage on all eighteen of them, which is worse than having none.
    //
    // It buys exactly one thing, and it is worth being precise about which: query
    // parameters. `/agents?utm_source=flyer` returns 200 with byte-identical content, so
    // every shared link carrying a tracking tag is a separate URL to a search engine.
    // The other duplicate shapes are already handled and do NOT need this — `/agents/`
    // and `/index.html` 308 to the canonical form, preview deploys carry
    // `x-robots-tag: noindex`, and lburg.org 301s, which is a directive rather than the
    // hint a canonical is.
    //
    // It does nothing for an agent. A canonical tells indexers which address to credit;
    // it authorises nothing, and no fetcher consults it before deciding what it may
    // request.
    const canonical = `<link rel="canonical" href="${SITE}${route}">`
    html = html.replace('</head>', `    ${canonical}\n  </head>`)
    if (!html.includes(canonical)) {
      failures.push(`${route}: could not inject the canonical link — no </head> found`)
      return
    }
    await write(route, html, text)

    await writeFile(cachedFile(route), html)
    deps[route] = {
      global, clock, external, date: today(), html: sha256(html),
      deps: Object.fromEntries(await Promise.all(read.map(async p => [p, await hashOf(p)]))),
    }
    done++
    const flags = [clock && 'clock', external && 'external'].filter(Boolean).join(', ')
    console.log(`  [${done}/${render.length}] ${route}${flags ? `  (reads ${flags})` : ''}` +
      `  ${((Date.now() - t0) / 1000).toFixed(0)}s`)
  }

  try {
    let next = 0
    await Promise.all(servers.map(async server => {
      while (next < render.length) await renderOne(render[next++], server)
    }))
  } finally {
    // WHETHER OR NOT THE RUN SUCCEEDED -- a build that dies half way is exactly the one
    // that used to leave 300 profiles behind.
    await sweepOurProfiles(startedAt)
    for (const s of servers) s.close()
    // Only routes this build still has; tmp + rename, so a killed run cannot leave half a
    // map that a later run would trust.
    const keep = Object.fromEntries(Object.entries(deps).filter(([r]) => all.includes(r)))
    await writeFile(`${CACHE_DEPS}.tmp`, JSON.stringify(keep, null, 1))
    await rename(`${CACHE_DEPS}.tmp`, CACHE_DEPS)
  }

  // Two routes rendering identical text means the router did not route -- most likely a
  // stale bundle that predates a page, since tabFromPath falls back to the root tab for
  // anything it does not recognise rather than erroring. That fallback is right for a
  // visitor following an old link and silent for us, so it is caught here: it is exactly
  // how /athletics was found being served as the front page.
  rows.sort((a, b) => routes.indexOf(a.route) - routes.indexOf(b.route))
  const byText = new Map()
  for (const r of rows) {
    const same = byText.get(r.text_body)
    if (same) {
      failures.push(`${r.route}: rendered text identical to ${same} — the router fell ` +
        'back to the root tab. Rebuild (npm run build); the bundle is probably stale.')
    } else byText.set(r.text_body, r.route)
  }

  const pad = Math.max(...rows.map(r => r.route.length), 8)
  console.log(`${'route'.padEnd(pad)}  ${'html'.padStart(9)}  ${'text'.padStart(8)}`)
  for (const r of rows) {
    console.log(`${r.route.padEnd(pad)}  ${r.bytes.toLocaleString().padStart(9)}  ` +
      `${r.text.toLocaleString().padStart(8)}`)
  }
  const secs = ((Date.now() - startedAt) / 1000).toFixed(0)
  console.log(`\n${rows.length}/${routes.length} routes written into dist/: ` +
    `rendered ${done}, reused ${reuse.length}, in ${secs}s`)

  if (failures.length) {
    console.error(`\n${failures.length} problem(s):`)
    for (const f of failures) console.error(`  - ${f}`)
    process.exit(1)
  }
  console.log('every route renders real HTML, keeps its script, and is in the sitemap.')
}

main().catch(e => { console.error(e); process.exit(1) })

/** Refuse to start a 332-route render with no room to write it.
 *
 *  2 GB is arbitrary and deliberately generous: dist/ is far smaller, but Chrome, npm and
 *  the OS all want scratch space, and the failure mode of running out half way is a
 *  half-written dist/ that later steps read as though it were complete. */
async function assertSpace(min = 2 * 1024 * 1024 * 1024) {
  const { stdout } = await execFileAsync('df', ['-k', DIST.split('/').slice(0, 3).join('/') || '/'])
  const free = Number(stdout.trim().split('\n').pop().split(/\s+/)[3]) * 1024
  if (Number.isFinite(free) && free < min) {
    const gb = n => `${(n / 1024 ** 3).toFixed(1)} GB`
    throw new Error(
      `only ${gb(free)} free on disk — refusing to prerender (want ${gb(min)}).\n` +
      `  Headless Chrome profiles are the usual cause. Check:\n` +
      `    du -sh ~/Library/Caches/Google/Chrome-headless\n` +
      `    find ~/Library/Caches/Google/Chrome-headless -maxdepth 1 -name 'scoped_dir*' -mtime +0 -exec rm -rf {} +`)
  }
}

/** Remove `scoped_dir*` profiles left by builds that ran before --user-data-dir was
 *  passed, and by any Chrome that died before cleaning up after itself.
 *
 *  Older than a day only. Anything newer may belong to a build running right now -- this
 *  repo has had four agents in one working tree, and deleting a live profile would fail
 *  somebody else's build in a way that looks like a bug in their code. */
async function sweepLeakedProfiles() {
  const dir = join(process.env.HOME || '', 'Library/Caches/Google/Chrome-headless')
  if (!existsSync(dir)) return
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  let names
  try { names = await readdir(dir) } catch { return }
  let gone = 0
  for (const name of names) {
    if (!name.startsWith('scoped_dir')) continue
    const p = join(dir, name)
    try {
      if ((await stat(p)).mtimeMs >= cutoff) continue
      await rm(p, { recursive: true, force: true })
      gone++
    } catch { /* a profile that vanished under us is the outcome we wanted */ }
  }
  if (gone) console.log(`swept ${gone} leaked Chrome profile(s) from earlier builds`)
}

/** Delete the Chrome profiles THIS run created.
 *
 *  Keyed on mtime against the run's start, so a build running concurrently in another
 *  worktree keeps its own -- this repo has had four agents in one tree, and deleting a
 *  live profile fails somebody else's build in a way that looks like a bug in their code.
 */
async function sweepOurProfiles(since) {
  const dir = join(process.env.HOME || '', 'Library/Caches/Google/Chrome-headless')
  if (!existsSync(dir)) return
  let names
  try { names = await readdir(dir) } catch { return }
  let gone = 0
  for (const name of names) {
    if (!name.startsWith('scoped_dir')) continue
    const p = join(dir, name)
    try {
      if ((await stat(p)).mtimeMs < since) continue
      await rm(p, { recursive: true, force: true })
      gone++
    } catch { /* vanished under us is the outcome we wanted */ }
  }
  if (gone) console.log(`cleaned up ${gone} Chrome profile(s) this run created`)
}
