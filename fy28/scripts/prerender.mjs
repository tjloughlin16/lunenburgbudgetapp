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
import { readFile, writeFile, mkdir, readdir, stat, rm } from 'node:fs/promises'
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
let PORT = 0

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
  const docs = (await readdir(join(APP, 'public', 'docs', 'analyses')))
    .filter(f => f.endsWith('.md')).map(f => f.slice(0, -3)).sort()
  if (!docs.length) throw new Error('no analyses in public/docs/analyses — nothing to render')
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
  return [...routes, ...docs.map(d => `/analysis/${d}`), ...posts.map(s => `/blog/${s}`), ...boards.map(s => `/boards/${s}`), ...finance, ...departments, ...meetings]
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

  const server = serve(shell)
  await new Promise(r => server.listen(0, r))
  PORT = server.address().port
  console.log(`serving dist/ on port ${PORT}`)
  // PREFLIGHT, BECAUSE ENOSPC DOES NOT PRESENT AS A DISK PROBLEM. When the disk filled on
  // 19 September 2026 the visible symptom was a prerender exiting 1 with no message, then
  // every unrelated command failing too. Fail here, with the reason, rather than there.
  await assertSpace()
  // And sweep what earlier builds leaked, so a machine that already has the problem heals
  // itself rather than needing somebody to know about it. Only what is a day old: a
  // concurrent build's profile is not ours to delete.
  await sweepLeakedProfiles()

  console.log(`prerendering ${routes.length} routes with ${chrome}\n`)

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
  try {

  for (const route of routes) {
    const url = `http://localhost:${PORT}${route}`
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
      continue
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
  } finally {
    // WHETHER OR NOT THE RUN SUCCEEDED -- a build that dies half way is exactly the one
    // that used to leave 300 profiles behind.
    await sweepOurProfiles(startedAt)
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
