/**
 * What does an agent actually SEE when it connects, and what would it conclude?
 *
 * `check-agents.mjs` proves the *server* is right: every route serves its own prerendered
 * text, missing documents 404, the published endpoint matches the app. It has been passing
 * while assistants kept reporting this site is an empty client-side shell. Both of those
 * can be true at once, and this script exists to show which one is happening, because
 * "the server is correct" and "the agent read it correctly" are different claims and only
 * the first one was ever checked.
 *
 * An agent's answer is the product of two things, and neither is the server alone:
 *
 *   WHERE it looked. "The site" is not one thing. It is reachable at the domain, at www,
 *   at the pages.dev alias, possibly at a Netlify build, at a local `dist/`, at a Vite dev
 *   server, and — still, in this repo — at a root-level `index.html` and `dist/` left from
 *   the app that came before `fy28/`. Some of those serve prerendered HTML and some serve
 *   a 693-byte empty div, and an agent told "check the site" does not report which one it
 *   fetched. A correct report about the wrong surface reads exactly like a wrong report.
 *
 *   HOW it read. A fetch is not a browser and it is not one pipeline either. Some readers
 *   take the whole body; some cap at a few KB and decide from that; every HTML-to-markdown
 *   converter drops comments, which is where this site's agent manifest lives; some answer
 *   from a pattern -- `<div id="root">` and a module script -- without measuring anything.
 *   Those four pipelines can reach four different verdicts on byte-identical HTML.
 *
 * So this prints a matrix: one row per surface, one column per reading pipeline, and in
 * each cell the verdict THAT reader would report. Where a cell says the site is a
 * client-side shell, the cell is the reproduction -- it names the surface and the pipeline
 * that produce the complaint.
 *
 *   node scripts/agent-view.mjs                       # every surface it can reach
 *   node scripts/agent-view.mjs --url https://...     # just one
 *   node scripts/agent-view.mjs --route /athletics    # a route other than the front page
 *   node scripts/agent-view.mjs --browser             # add headless Chrome as ground truth
 *   node scripts/agent-view.mjs --cache               # the cache-buster probe, §4
 *   node scripts/agent-view.mjs --links               # §6: is every published URL LINKED
 *
 * Needs Node 22 (WebSocket, for --browser):  source ~/.nvm/nvm.sh && nvm use 22
 */
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, dirname, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const APP = join(HERE, '..')
const REPO = join(APP, '..')

const arg = (name, fallback = null) =>
  process.argv.includes(name) ? process.argv[process.argv.indexOf(name) + 1] : fallback
const flag = (name) => process.argv.includes(name)

const ROUTE = arg('--route', '/athletics')

/**
 * A reader is judged to have "found the page" at 2,000 characters of visible text, the
 * same threshold check-agents.mjs uses for a route being prerendered. The empty shell
 * yields 0; the thinnest real route yields five figures. Nothing sits near the line.
 */
const CONTENT = 2000

/**
 * Every surface this site is reachable at. The last three are the ones that matter to the
 * complaint: they are live, they are plausible things to be pointed at, and they do not
 * serve what production serves.
 */
const SURFACES = [
  { name: 'production', url: 'https://lunenburgbudgetproject.org', note: 'the deployed site' },
  { name: 'www', url: 'https://www.lunenburgbudgetproject.org', note: 'same build, other host' },
  { name: 'pages.dev', url: 'https://lunenburg-fy28.pages.dev', note: 'Cloudflare alias' },
  { name: 'netlify', url: 'https://lunenburgbudgetproject.netlify.app',
    note: 'netlify.toml builds `npm run build` — the UN-prerendered SPA' },
  { name: 'vite dev', url: 'http://127.0.0.1:5173',
    note: 'npm run dev — never prerendered, by design' },
  { name: 'local dist', dir: join(APP, 'dist'), note: 'fy28/dist — what deploy uploads' },
  { name: 'repo root', dir: REPO, note: 'the pre-fy28 app, still in the working tree' },
]

/* ---------------------------------------------------------------- text extraction */

/**
 * Visible text, the way anything that does not run JavaScript would arrive at it.
 *
 * Measured from `<div id="root">` and nowhere else. An earlier version fell back to the
 * whole document when the root was not in the window, which scored 2,244 characters of
 * inlined CSS for a reader that had not reached the body yet -- a check reporting that a
 * truncated reader found the page, when what it found was the stylesheet.
 */
function visibleText(html) {
  const i = html.indexOf('<div id="root"')
  if (i < 0) return ''
  const body = html.slice(i)
  return body
    .replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;|&#\d+;/gi, ' ')
    .replace(/\s+/g, ' ').trim()
}

/** Where in the byte stream does the first rendered content actually begin? */
function contentOffset(html) {
  const i = html.indexOf('<div id="root">')
  if (i < 0) return -1
  // An empty root is not content. Look for the first tag inside it.
  return /^<div id="root">\s*<\/div>/.test(html.slice(i)) ? -1 : i
}

/* ---------------------------------------------------------------- the four pipelines */

/**
 * Each takes the fetched HTML and returns what that kind of reader ends up with, plus the
 * verdict it would report. `ok` means it found the page; `false` means it would tell the
 * user this site renders client-side.
 */
const PIPELINES = [
  {
    name: 'whole body',
    why: 'curl, python-requests, a fetch tool that reads the entire response',
    read: (html) => {
      const t = visibleText(html)
      return { ok: t.length >= CONTENT, detail: `${t.length.toLocaleString()} chars` }
    },
  },
  {
    /**
     * The one that matters. Content on this site starts 9,249 bytes in: ~5KB of head and
     * inlined styles, then the 4.2KB agent-manifest comment, and only then the first
     * rendered element. A reader that caps at 8KB and decides from what it has sees a
     * `<div id="root">` it never reaches the end of, no text at all, and is not wrong to
     * call that an empty shell. It is reading a real prerendered page.
     */
    name: 'first 8KB',
    why: 'a reader that caps the body — see the cliff below for where the cap bites',
    read: (html) => {
      const cut = html.slice(0, 8192)
      const t = visibleText(cut)
      return { ok: t.length >= CONTENT, detail: `${t.length.toLocaleString()} chars in 8KB` }
    },
  },
  {
    name: 'html→markdown',
    why: 'WebFetch and every reader that converts before the model sees it',
    read: (html) => {
      // Comments are dropped by every converter, so the manifest is invisible here even
      // though it is the first thing in the file.
      const t = visibleText(html)
      const manifest = /BEGIN AGENT MANIFEST/.test(html)
      return {
        ok: t.length >= CONTENT,
        detail: `${t.length.toLocaleString()} chars` +
          (manifest ? '; manifest present in HTML but stripped as a comment' : ''),
      }
    },
  },
  {
    /**
     * No measurement at all: the shape of the document is read as its nature. This is the
     * pipeline that produces the complaint most confidently, because `<div id="root">` and
     * a module bundle are exactly what an un-prerendered React app looks like — and are
     * also still what a prerendered one looks like, in the first line of its body.
     */
    name: 'shape sniff',
    why: 'answering from `<div id="root">` + a module script, measuring nothing',
    read: (html) => {
      const empty = /<div id="root">\s*<\/div>/.test(html)
      const bundle = /<script[^>]+type="module"/.test(html)
      return {
        ok: !empty,
        detail: empty ? 'empty root + module script → "client-side"'
          : bundle ? 'root has children; bundle present' : 'root has children',
      }
    },
  },
]

/* ---------------------------------------------------------------- fetching a surface */

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.csv': 'text/csv', '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml', '.md': 'text/markdown',
}

/** Serve a directory the way a static host does: real file, else <slug>.html, else shell. */
function serveDir(root, port) {
  const server = createServer(async (req, res) => {
    const p = decodeURIComponent(new URL(req.url, 'http://x').pathname)
    for (const f of [p === '/' ? 'index.html' : p.slice(1), `${p.slice(1)}.html`, 'index.html']) {
      const abs = join(root, f)
      if (f && existsSync(abs)) {
        try {
          const buf = await readFile(abs)
          res.writeHead(200, { 'content-type': MIME[extname(abs)] || 'application/octet-stream' })
          return res.end(buf)
        } catch { /* a directory; try the next candidate */ }
      }
    }
    res.writeHead(404).end('not found')
  })
  return new Promise((ok) => server.listen(port, '127.0.0.1', () => ok(server)))
}

async function fetchSurface(s, port) {
  let server
  let base = s.url
  if (s.dir) {
    if (!existsSync(join(s.dir, 'index.html'))) return { skip: 'no index.html on disk' }
    server = await serveDir(s.dir, port)
    base = `http://127.0.0.1:${port}`
  }
  try {
    const res = await fetch(base + ROUTE, { signal: AbortSignal.timeout(15000) })
    const html = await res.text()
    return { status: res.status, html, base }
  } catch (e) {
    return { skip: e.name === 'TimeoutError' ? 'timed out' : 'not reachable' }
  } finally {
    server?.close()
  }
}

/* ---------------------------------------------------------------- output */

const PAD = 13
const cell = (r) => (r.ok ? ' reads it ' : ' CLIENT-SIDE')

async function matrix() {
  console.log(`\nWhat an agent sees at ${ROUTE}\n`)
  console.log('Two things decide the answer: which surface it fetched, and how it reads.')
  console.log(`A cell says CLIENT-SIDE where that reader would report an empty shell.\n`)

  const header = 'surface'.padEnd(PAD) + PIPELINES.map(p => p.name.padEnd(16)).join('')
  console.log(header)
  console.log('-'.repeat(header.length))

  const rows = []
  let port = 8820
  for (const s of SURFACES) {
    const got = await fetchSurface(s, port++)
    if (got.skip) {
      console.log(s.name.padEnd(PAD) + `— ${got.skip}`)
      continue
    }
    if (got.status !== 200) {
      console.log(s.name.padEnd(PAD) + `— HTTP ${got.status}; nothing served here to read`)
      continue
    }
    const results = PIPELINES.map(p => ({ p, r: p.read(got.html) }))
    console.log(s.name.padEnd(PAD) + results.map(({ r }) => cell(r).padEnd(16)).join('')
      + `  ${got.status}  ${got.html.length.toLocaleString()}b`)
    rows.push({ s, got, results })
  }

  console.log('\nthe surfaces, and what each one is')
  for (const s of SURFACES) console.log(`  ${s.name.padEnd(PAD)} ${s.note}`)

  console.log('\nthe readers, and who reads that way')
  for (const p of PIPELINES) console.log(`  ${p.name.padEnd(PAD)} ${p.why}`)

  console.log('\nwhere the content starts, in bytes')
  for (const { s, got } of rows) {
    const off = contentOffset(got.html)
    console.log(`  ${s.name.padEnd(PAD)} ` + (off < 0
      ? 'no rendered content at all; root is empty'
      : `first rendered element at byte ${off.toLocaleString()}` +
        (off > 8192 ? '  — PAST an 8KB cap' : '')))
  }

  // WHICH readers cap their input is not established here and this script cannot see it.
  // Where this page's content begins is a measurement, and it is the whole exposure: any
  // reader whose cap falls below that offset sees a document with no body text in it.
  const live = rows.find(({ got }) => contentOffset(got.html) > 0)
  if (live) {
    const html = live.got.html
    const off = contentOffset(html)
    console.log(`\nthe cliff — content begins at byte ${off.toLocaleString()}, so a reader that`)
    console.log('caps below that reads a document with an empty body:')
    for (const cap of [2048, 4096, 8192, 16384, 32768]) {
      const t = visibleText(html.slice(0, cap))
      console.log(`  cap ${String(cap).padStart(6)}b  ${t.length ? `${t.length.toLocaleString()} chars` : 'NOTHING — would report a client-side shell'}`)
    }
    const head = html.slice(0, off)
    // The manifest is two comments, not one -- a `<!--BEGIN AGENT MANIFEST-->` marker and
    // the block itself. Matching only the marker measured 27 bytes and made the manifest
    // look incidental to the offset. Sum every comment ahead of the content instead.
    const comments = [...head.matchAll(/<!--[\s\S]*?-->/g)].reduce((n, m) => n + m[0].length, 0)
    console.log(`  of those ${off.toLocaleString()} bytes, ${comments.toLocaleString()} are HTML comments —`)
    console.log('  the agent manifest, which every html→markdown reader drops before the model')
    console.log(`  sees it. The other ${(off - comments).toLocaleString()} are head, meta and inlined CSS.`)
  }

  console.log('\ndetail')
  for (const { s, results } of rows) {
    for (const { p, r } of results) {
      console.log(`  ${s.name.padEnd(PAD)} ${p.name.padEnd(15)} ${r.detail}`)
    }
  }

  const broken = rows.filter(({ results }) => results.some(r => !r.r.ok))
  console.log()
  if (!broken.length) {
    console.log('No reader on any reachable surface would report a client-side shell.')
  } else {
    console.log('These combinations produce the complaint. Each is a reproduction:')
    for (const { s, results } of broken) {
      for (const { p, r } of results.filter(x => !x.r.ok)) {
        console.log(`  ${s.name} read as "${p.name}" → ${r.detail}`)
      }
    }
  }
  return rows
}

/* ---------------------------------------------------------------- §4 the cache probe */

/**
 * On 30 August an agent reported the site was client-side hours after it was prerendered
 * and deployed. It was reading a cached response, and its own `?nocache=` attempt had been
 * NORMALISED AWAY — the param stripped, the request folded onto the same cache entry — so
 * the fetch looked fresh and was not. A cache-buster that gets normalised is worse than
 * none: it produces a confident wrong answer. This shows which busters survive.
 */
async function cacheProbe() {
  const base = arg('--url', 'https://lunenburgbudgetproject.org')
  console.log(`\ncache-buster probe against ${base}${ROUTE}\n`)
  const busters = ['', `?nocache=${Date.now()}`, `?v=${Date.now() % 1000}`, `?_=${Date.now()}`]
  for (const q of busters) {
    try {
      const res = await fetch(base + ROUTE + q, { signal: AbortSignal.timeout(15000) })
      const html = await res.text()
      // res.url is the URL that actually got fetched. If the param is gone from it, the
      // buster was dropped and this response may be the same cache entry as the bare one.
      const kept = q === '' || res.url.includes(q.slice(1).split('=')[0])
      console.log(`  ${(q || '(none)').padEnd(22)} ${res.status}  ` +
        `${String(res.headers.get('cf-cache-status') || '-').padEnd(9)} ` +
        `age=${String(res.headers.get('age') || '-').padEnd(6)} ` +
        `${visibleText(html).length.toLocaleString().padStart(8)} chars  ` +
        `${kept ? 'param survived' : 'PARAM STRIPPED — same cache entry, looks fresh'}`)
    } catch (e) {
      console.log(`  ${(q || '(none)').padEnd(22)} ${e.message}`)
    }
  }
}

/* ---------------------------------------------------------------- §5 ground truth */

async function browserTruth(rows) {
  const { launch, sleep } = await import('./_cdp.mjs')
  console.log('\nheadless Chrome, for comparison — what a person with JavaScript gets')
  const chrome = await launch(9346)
  try {
    for (const { s, got } of rows) {
      if (!got.base?.startsWith('http')) continue
      const page = await chrome.newPage()
      await page.send('Page.navigate', { url: got.base + ROUTE })
      await sleep(2500)
      const n = await page.eval('document.body.innerText.replace(/\\s+/g," ").trim().length')
      console.log(`  ${s.name.padEnd(PAD)} ${String(n).padStart(8)} chars after JavaScript`)
      page.close()
    }
  } finally { chrome.proc.kill() }
}

/* ---------------------------------------------------------------- §6 the link graph */

/**
 * Every URL this site publishes must be reachable by following LINKS from the home page.
 *
 * `llms.txt` names them all and that turned out not to be enough, for a reason that took
 * three separate incidents to see. Assistants commonly refuse to fetch a URL that has not
 * appeared in something they already fetched -- a provenance guardrail, and a sound one.
 * `llms.txt` is text/plain, so the URLs in it are TEXT. An assistant read it, found the
 * bundle it needed named there, and was not permitted to request it: "my fetcher will only
 * take URLs it's already seen in a page or search result."
 *
 * So llms.txt DESCRIBES the archive and the link graph AUTHORIZES it, and only the second
 * one was ever checked -- by nothing. When this was written, `/minutes/school-committee.txt`
 * and `/minutes/INDEX.txt` appeared in no anchor anywhere on the site, and the only
 * `/minutes` link that existed pointed at `/minutes/`, a directory that correctly 404s.
 *
 * Two hops, because that is the shape the site is built to: the footer carries the handful
 * that matter and links `/agents`, which carries the rest. A third hop would mean an index
 * pointing at an index, which is a fetch an agent has to spend and a place it can give up.
 *
 * Exits non-zero, so it can gate a deploy.
 */
async function linkGraph() {
  const base = arg('--url', null)
  const dist = join(APP, 'dist')
  let server, root = base
  if (!base) {
    if (!existsSync(join(dist, 'index.html'))) {
      console.error('no dist/ — run `npm run build:site` first')
      process.exit(1)
    }
    server = await serveDir(dist, 8830)
    root = 'http://127.0.0.1:8830'
  }

  const hrefs = async (path) => {
    const res = await fetch(root + path)
    if (!res.status || res.status >= 400) return []
    const html = await res.text()
    if (!(res.headers.get('content-type') || '').includes('text/html')) return []
    return [...html.matchAll(/href="([^"]+)"/g)]
      .map(m => m[1].replace(/^\.\//, '/'))
      .filter(u => u.startsWith('/'))
  }

  // Hop 1: the home page. Hop 2: everything it links that is itself a page.
  const hop1 = await hrefs('/')
  const reachable = new Set(hop1)
  for (const u of hop1) {
    if (/\.[a-z0-9]+$/i.test(u)) continue      // a file, not a page to expand
    for (const v of await hrefs(u)) reachable.add(v)
  }

  // What llms.txt promises. Its own text is the specification of what must be linked.
  const llms = await (await fetch(root + '/llms.txt')).text()
  const promised = [...new Set(
    [...llms.matchAll(/https:\/\/lunenburgbudgetproject\.org(\/[^\s)\]<>"']+)/g)]
      .map(m => m[1].replace(/[.,`)\]]+$/, '')))]
    // A pattern with a placeholder is documentation, and a bare prefix ending in `/` is a
    // directory rather than a file. Neither is an address anything can fetch.
    .filter(u => !u.includes('<') && !u.includes('*') && !u.endsWith('/'))

  console.log(`\nlink graph — ${promised.length} URLs named in llms.txt, ` +
    `${reachable.size} reachable in two hops from /\n`)

  // Reachability is not enough, and assuming it was is what let this ship broken.
  //
  // The footer carried every one of these links and the front page is 250KB, so they sat
  // at 95% of the document -- past where any fetch tool stops. A check that asked "is it
  // linked?" passed the whole time an assistant was reporting it could not reach /api/index.
  // `/api/lines`, 121KB, comes back truncated mid-record, so the ceiling is far below the
  // size of a page. Assert the POSITION, in converted text, the way a reader meets it.
  const CUTOFF = 50000
  const home = await (await fetch(root + '/')).text()
  const asText = home.slice(Math.max(0, home.indexOf('<div id="root"')))
    .replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
  const KEY = ['/agents', '/llms.txt', '/api/index', '/minutes/INDEX.txt']
  const late = []
  console.log(`\nwhere the agent links sit in the front page, as converted text`)
  for (const u of KEY) {
    const i = asText.indexOf(`href="${u}"`)
    const chars = i < 0 ? -1 : asText.slice(0, i).replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ').length
    console.log(`  ${u.padEnd(22)} ` + (i < 0 ? 'NOT ON THE FRONT PAGE'
      : `${chars.toLocaleString().padStart(8)} chars in` + (chars > CUTOFF ? '  — PAST THE CUT' : '')))
    if (i < 0 || chars > CUTOFF) late.push(`${u}: ${i < 0 ? 'absent' : `${chars} chars in`}`)
  }

  const orphans = promised.filter(u => !reachable.has(u))
  if (orphans.length) {
    console.log(`${orphans.length} named in llms.txt and linked from nowhere:`)
    for (const u of orphans) console.log(`  ${u}`)
    console.log('\nAn assistant that only fetches URLs it has seen in a page cannot reach')
    console.log('these. Add them to src/components/AgentsIndex.tsx, which is generated from')
    console.log('agent-manifest.json — the same file llms.txt is built from.')
  } else {
    console.log('every URL llms.txt names is reachable by following links. ' +
      'Nothing is described but unlinked.')
  }

  // The inverse failure, and the one that put the only /minutes link on a 404: a link that
  // goes nowhere is worse than a missing one, because it looks like an answer.
  const dead = []
  for (const u of [...reachable].filter(u => !u.startsWith('/#'))) {
    const res = await fetch(root + u, { redirect: 'manual' })
    if (res.status >= 400) dead.push(`${u} → ${res.status}`)
  }
  console.log(dead.length ? `\n${dead.length} link(s) on the site lead to an error:` : '\nno linked URL 404s.')
  for (const d of dead) console.log(`  ${d}`)

  if (late.length) {
    console.log(`\n${late.length} agent link(s) are absent or too far into the front page.`)
    console.log(`A reader that converts and caps never reaches them, so they are linked and`)
    console.log(`unreachable — which is the state this check exists to catch. Keep them in`)
    console.log(`DataTopLine.tsx, above the content, not only in the footer.`)
  }

  server?.close()
  if (orphans.length || dead.length || late.length) process.exit(1)
}

async function main() {
  if (flag('--links')) return linkGraph()
  if (flag('--cache')) return cacheProbe()
  const single = arg('--url')
  if (single) SURFACES.splice(0, SURFACES.length, { name: 'given', url: single, note: single })
  const rows = await matrix()
  if (flag('--browser')) await browserTruth(rows)
}

main().catch(e => { console.error(e); process.exit(1) })
