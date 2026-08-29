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
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises'
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
const PORT = 8794

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
  // '' is the root. Everything else is a path segment.
  return slugs.map(s => (s ? `/${s}` : '/'))
}

/** Serve dist, falling back to the PRISTINE shell.
 *
 *  Pristine matters: this script overwrites dist/index.html with the rendered root. Without
 *  holding the original in memory, a second run would prerender a page that was already
 *  prerendered, nesting the output. Serving from memory makes the script idempotent. */
function serve(shell) {
  return createServer(async (req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname)
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
    res.end(shell)
  })
}

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

  const routes = await readRoutes()
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

  const server = serve(shell)
  await new Promise(r => server.listen(PORT, r))
  console.log(`prerendering ${routes.length} routes with ${chrome}\n`)

  const failures = []
  const rows = []

  for (const route of routes) {
    const url = `http://localhost:${PORT}${route}`
    let html
    try {
      const { stdout } = await execFileAsync(chrome, [
        '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
        // React and recharts settle on timers; virtual time lets Chrome run them to
        // completion immediately rather than us guessing at a sleep.
        '--virtual-time-budget=10000',
        '--run-all-compositor-stages-before-draw',
        '--dump-dom', url,
      ], { maxBuffer: 64 * 1024 * 1024 })
      html = preamble + stdout.slice(stdout.indexOf('<html'))
    } catch (e) {
      failures.push(`${route}: chrome failed — ${e.message.split('\n')[0]}`)
      continue
    }

    const text = visibleText(html)
    if (text.length < MIN_TEXT) {
      failures.push(`${route}: rendered only ${text.length} chars of text (min ${MIN_TEXT})`)
      continue
    }
    if (!html.includes(scriptTag[1])) {
      failures.push(`${route}: rendered HTML lost the module script ${scriptTag[1]}`)
      continue
    }
    if (!html.startsWith(preamble)) {
      failures.push(`${route}: lost the doctype/agent-comment preamble`)
      continue
    }
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

  // Two routes rendering identical text means the router did not route -- most likely a
  // stale bundle that predates a page, since tabFromPath falls back to the root tab for
  // anything it does not recognise rather than erroring. That fallback is right for a
  // visitor following an old link and silent for us, so it is caught here: it is exactly
  // how /athletics was found being served as the front page.
  const byText = new Map()
  for (const r of rows) {
    const same = byText.get(r.text_body)
    if (same) {
      failures.push(`${r.route}: rendered text identical to ${same} — the router fell ` +
        'back to the root tab. Rebuild (npm run build); the bundle is probably stale.')
    } else byText.set(r.text_body, r.route)
  }

  server.close()

  const pad = Math.max(...rows.map(r => r.route.length), 8)
  console.log(`${'route'.padEnd(pad)}  ${'html'.padStart(9)}  ${'text'.padStart(8)}`)
  for (const r of rows) {
    console.log(`${r.route.padEnd(pad)}  ${r.bytes.toLocaleString().padStart(9)}  ` +
      `${r.text.toLocaleString().padStart(8)}`)
  }
  console.log(`\n${rows.length}/${routes.length} routes written into dist/`)

  if (failures.length) {
    console.error(`\n${failures.length} problem(s):`)
    for (const f of failures) console.error(`  - ${f}`)
    process.exit(1)
  }
  console.log('every route renders real HTML, keeps its script, and is in the sitemap.')
}

main().catch(e => { console.error(e); process.exit(1) })
