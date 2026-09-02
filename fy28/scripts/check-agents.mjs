/**
 * Check the site answers correctly to something that does not run JavaScript.
 *
 * Runs the built output under the real Cloudflare Pages runtime (`wrangler pages dev`,
 * which loads `functions/` and `_redirects` exactly as production does) and asserts the
 * four behaviours that matter to a reader, a crawler or an assistant fetching a URL:
 *
 *   1. **Every app route serves its own content.** Before prerendering, all fourteen
 *      returned a byte-identical 6,122-byte shell whose body was `<div id="root"></div>`.
 *      So this checks not just that a route has text, but that no two routes have the
 *      SAME text — which is how a stale bundle serving the front page under /athletics
 *      was found.
 *   2. **Aliases and stale links still resolve.** `routes.ts` deliberately sends an
 *      unrecognized path to the front page rather than an error. Adding a real 404 must
 *      not take that with it.
 *   3. **Archive documents that exist are served as themselves**, not as HTML.
 *   4. **Archive documents that do not exist return 404.** This is the one that was
 *      silently wrong: a missing source document answered `200 OK` with the app shell,
 *      so nothing reading status codes could tell it from a document that was there.
 *
 * Point it at production instead of a local build with:
 *     node scripts/check-agents.mjs --url https://lunenburgbudgetproject.org
 *
 * Needs Node 22 for wrangler:  source ~/.nvm/nvm.sh && nvm use 22
 */
import { spawn, execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const APP = join(HERE, '..')
const DIST = join(APP, 'dist')
const PORT = 8802

const argUrl = process.argv.includes('--url')
  ? process.argv[process.argv.indexOf('--url') + 1] : null

// Present in the deployed archive. Chosen to cover the file types the archive actually
// holds, because "the .md files are served" and "the PDFs are served" are separate claims.
const PRESENT = [
  '/llms.txt', '/robots.txt', '/sitemap.xml',
  '/data/model.json', '/data/sources.json', '/data/budget-lines.csv',
  '/docs/analyses/sped-and-the-curve.md',
  // The meeting archive. Its text went unpublished for months while llms.txt said it was
  // "in the repository", and an assistant asked for the School Committee's discussion of
  // the para contract concluded from this site that we hold no minutes at all. Checked
  // here so that cannot recur silently.
  '/minutes/INDEX.txt',
  '/minutes/school-committee.txt',
  '/docs/minutes/text/school-committee/2025-02-26-minutes-7076.txt',
]
// Must 404. Deliberately plausible-looking, because the failure being tested for is a
// missing document that answers exactly like a present one.
const ABSENT = [
  '/docs/analyses/no-such-analysis.md',
  '/docs/pdf/no-such-document.pdf',
  '/docs/xlsx/no-such-workbook.xlsx',
  '/data/no-such-endpoint.json',
]
// Not routes. Must still land on the app, per routes.ts.
const STALE = ['/an-old-shared-link', '/sports', '/documents', '/evidence']

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

function textOf(html) {
  const body = html.slice(Math.max(0, html.indexOf('<div id="root"')))
  return body.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ').replace(/&[a-z]+;|&#\d+;/gi, ' ')
    .replace(/\s+/g, ' ').trim()
}

async function readRoutes() {
  const src = await readFile(join(APP, 'src', 'routes.ts'), 'utf8')
  const block = src.match(/export const SLUG: Record<Tab, string> = \{([\s\S]*?)\n\}/)
  // Unlisted routes are excluded, for the same reason prerender.mjs skips them: they are
  // deliberately not prerendered, so they serve the app shell and would fail the
  // "identical text to /" test that catches a genuinely unrouted page. They still work —
  // the SPA fallback serves index.html and React routes it — they simply have no static
  // twin for a fetcher to read. Checked separately below.
  const unlisted = new Set(
    [...(src.match(/export const UNLISTED[^\n]*\n/) ?? [''])[0]
      .matchAll(/'([a-z]+)'/g)].map(m => m[1]))
  return [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)]
    .filter(m => !unlisted.has(m[1]))
    .map(m => (m[2] ? `/${m[2]}` : '/'))
}

/** Unlisted routes: must answer 200 with the app shell, and must NOT be in the sitemap. */
async function readUnlistedRoutes() {
  const src = await readFile(join(APP, 'src', 'routes.ts'), 'utf8')
  const block = src.match(/export const SLUG: Record<Tab, string> = \{([\s\S]*?)\n\}/)
  const unlisted = new Set(
    [...(src.match(/export const UNLISTED[^\n]*\n/) ?? [''])[0]
      .matchAll(/'([a-z]+)'/g)].map(m => m[1]))
  return [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)]
    .filter(m => unlisted.has(m[1]))
    .map(m => `/${m[2]}`)
}

async function main() {
  const routes = await readRoutes()
  let base = argUrl
  let wrangler

  if (!base) {
    if (!existsSync(join(DIST, 'index.html'))) {
      console.error('no dist/ — run `npm run build:site` first')
      process.exit(1)
    }
    base = `http://127.0.0.1:${PORT}`
    wrangler = spawn('npx', ['wrangler', 'pages', 'dev', 'dist',
      '--port', String(PORT), '--ip', '127.0.0.1'],
      { cwd: APP, stdio: 'ignore' })
    let up = false
    for (let i = 0; i < 60 && !up; i++) {
      await sleep(1000)
      try { await fetch(base); up = true } catch { /* still starting */ }
    }
    if (!up) { wrangler.kill(); throw new Error('wrangler pages dev never came up') }
  }

  const fails = []
  const seen = new Map()

  console.log(`checking ${base}\n`)
  console.log('app routes — status, and the visible text a non-JS reader gets')
  for (const r of routes) {
    const res = await fetch(base + r, { redirect: 'manual' })
    const html = res.status === 200 ? await res.text() : ''
    const text = html ? textOf(html) : ''
    console.log(`  ${String(res.status).padEnd(4)} ${r.padEnd(24)} ${text.length.toLocaleString().padStart(8)} chars`)
    if (res.status !== 200) fails.push(`${r}: status ${res.status}, expected 200 with no redirect`)
    else if (text.length < 2000) fails.push(`${r}: only ${text.length} chars — not prerendered`)
    else {
      const dup = seen.get(text)
      if (dup) fails.push(`${r}: identical text to ${dup} — the router did not route`)
      else seen.set(text, r)
    }
  }

  // Unlisted pages: reachable by address, findable by nothing. The three things that
  // make that true are checked, because "we just didn't link it" is not a mechanism.
  const unlisted = await readUnlistedRoutes()
  if (unlisted.length) {
    console.log('\nunlisted routes — must work by address and appear in no index')
    const sitemap = await (await fetch(base + '/sitemap.xml')).text()
    const robots = await (await fetch(base + '/robots.txt')).text()
    for (const r of unlisted) {
      const res = await fetch(base + r)
      const inMap = sitemap.includes(r + '<')
      // Deliberately absent from robots.txt too: a Disallow line is served publicly to
      // anyone who asks, so listing the path there advertises the thing it hides.
      const inRobots = robots.includes(r)
      console.log(`  ${String(res.status).padEnd(4)} ${r.padEnd(24)} ` +
        `sitemap:${inMap ? 'LISTED' : 'no'}  robots:${inRobots ? 'LISTED' : 'no'}`)
      if (res.status !== 200) fails.push(`${r}: status ${res.status} — an unlisted page must still answer`)
      if (inMap) fails.push(`${r}: is in sitemap.xml, which is the opposite of unlisted`)
      if (inRobots) fails.push(`${r}: named in robots.txt, which advertises it to anyone who reads that file`)
      if (existsSync(join(DIST, r.slice(1) + '.html'))) {
        fails.push(`${r}: was prerendered into dist — an unlisted page should leave no static file`)
      }
    }
  }

  console.log('\nthe API must answer as JSON, and say where its figures came from')
  for (const p of ['/api/index', '/api/schema', '/api/totals']) {
    const res = await fetch(base + p)
    const type = res.headers.get('content-type') || ''
    console.log(`  ${String(res.status).padEnd(4)} ${p.padEnd(24)} ${type.split(';')[0]}`)
    if (res.status !== 200) fails.push(`${p}: status ${res.status}, expected 200`)
    else if (!type.includes('application/json')) fails.push(`${p}: served ${type}, expected JSON`)
  }
  {
    // Rule 12 in API form: a figure with no address is not publishable.
    //
    // Checked on more than one resource on purpose. The first version of this check
    // looked only at /api/ledger, passed, and shipped 415 per-line files whose
    // provenance was an empty array -- the doc_id in budget_figure is a bare filename
    // and the document table is keyed by archive path, so the lookup silently matched
    // nothing. One resource passing says nothing about the others.
    for (const p of ['/api/ledger', '/api/lines/classified-ads', '/api/workbook/fy2025']) {
      const res = await fetch(base + p)
      const body = res.ok ? await res.json() : {}
      const prov = body.provenance || {}
      const n = Array.isArray(prov.documents) ? prov.documents.length : 0
      const unresolved = (prov.unresolved || []).length
      console.log(`  ${n > 0 ? ' ok ' : 'FAIL'} ${p.padEnd(30)} provenance: ` +
        `${n} document(s)${unresolved ? `, ${unresolved} UNRESOLVED` : ''}`)
      if (!n) fails.push(`${p} returned rows with no resolvable provenance`)
      if (unresolved) fails.push(`${p} cites ${unresolved} document(s) with no address`)
    }
  }
  {
    // The published database must be the bytes the API says it is.
    const claimed = (await (await fetch(base + '/api/index')).json())
      .endpoints.find(e => e.url.endsWith('lunenburg.db'))
    const buf = Buffer.from(await (await fetch(base + '/data/lunenburg.db')).arrayBuffer())
    const got = createHash('sha256').update(buf).digest('hex')
    const same = claimed && claimed.about.includes(got)
    console.log(`  ${same ? ' ok ' : 'FAIL'} /data/lunenburg.db sha256 ${got.slice(0, 12)} ` +
      `matches what /api/index claims`)
    if (!same) fails.push('/data/lunenburg.db does not match the sha256 published in /api/index')
  }
  {
    const res = await fetch(base + '/api/no-such-resource')
    const type = res.headers.get('content-type') || ''
    const ok = res.status === 404 && type.includes('application/json')
    console.log(`  ${ok ? ' ok ' : 'FAIL'} /api/no-such-resource → ${res.status} ${type.split(';')[0]}`)
    if (!ok) fails.push('/api/<missing> must 404 as JSON, not 200 with the app shell')
  }

  // llms.txt is the ONE surface built for readers who will not check anything else, so
  // a figure that drifts there is worse than a figure that drifts on a page. It drifted:
  // the file published the FY27 appropriation without the Special Town Meeting article
  // that every page uses, and published the FY28-FY30 average under a label saying FY28.
  // Both were found by an agent reading the site, not by anything here.
  console.log('\nllms.txt figures must match the model the app renders from')
  {
    const model = JSON.parse(await readFile(join(APP, 'src', 'data', 'model.json'), 'utf8'))
    const txt = await (await fetch(base + '/llms.txt')).text()
    const usd = (n) => '$' + Math.round(n).toLocaleString('en-US')
    // model.fy27.lps_appropriation is the field llms.txt renders. sped.appropriation is
    // the same quantity rebuilt from line items and differs by $1.50, so checking against
    // the wrong one fails on rounding and teaches nothing.
    const appropriation = model.fy27?.lps_appropriation
    const stm = model.fy27?.stm_appropriation
    const firstYear = model.freeCash?.deficits?.[0]?.amount
    const checks = [
      ['FY27 appropriation as adopted', appropriation && usd(appropriation)],
      ['FY27 appropriation after the STM', appropriation && stm && usd(appropriation + stm)],
      ['FY28 shortfall, first year alone', firstYear && usd(firstYear)],
    ]
    for (const [label, needle] of checks) {
      if (!needle) { fails.push(`llms.txt check "${label}": could not derive it from model.json`); continue }
      const ok = txt.includes(needle)
      console.log(`  ${ok ? ' ok ' : 'FAIL'} ${label.padEnd(38)} ${needle}`)
      if (!ok) fails.push(`llms.txt does not carry ${needle} for ${label} — run ` +
        '`python3 scripts/build_agent_endpoints.py`')
    }
    // The label/value mismatch that started this: the three-year average must never be
    // the only figure offered under an FY28 heading.
    if (/FY28 gap/i.test(txt) && firstYear && !txt.includes(usd(firstYear))) {
      fails.push('llms.txt labels a figure "FY28 gap" without also giving the first-year ' +
        'shortfall — that is the mismatch an agent reported')
    }
  }

  // The prefixes an agent guesses first. Each must answer with something a PROGRAM can
  // act on, never with 200 and the app shell -- which is what /minutes/ did, and is why
  // two assistants in a row concluded this site does not hold the meeting minutes.
  console.log('\nguessable archive paths must not answer 200 with the app shell')
  for (const p of ['/minutes/', '/minutes', '/docs/', '/minutes/school-committee',
                   '/minutes/index.txt']) {
    const res = await fetch(base + p)
    const type = res.headers.get('content-type') || ''
    const shell = res.status === 200 && type.includes('text/html')
    console.log(`  ${shell ? 'FAIL' : ' ok '} ${p.padEnd(30)} ${res.status} ${type.split(';')[0]}`)
    if (shell) fails.push(`${p} answers 200 with the app shell — a program reading this ` +
      'concludes the archive is not served')
  }
  {
    // And the 404 has to be useful: it is the only message a program will ever read.
    const res = await fetch(base + '/minutes/')
    const body = await res.text()
    const teaches = body.includes('/minutes/school-committee.txt')
      && body.includes('/docs/minutes/text/')
    console.log(`  ${teaches ? ' ok ' : 'FAIL'} /minutes/ 404 names the URLs that do work`)
    if (!teaches) fails.push('/minutes/ returns a 404 that does not say what to fetch instead')
  }

  console.log('\nstale and aliased links — must still reach the app')
  for (const p of STALE) {
    const res = await fetch(base + p)
    console.log(`  ${String(res.status).padEnd(4)} ${p}`)
    if (res.status !== 200) fails.push(`${p}: status ${res.status}, expected 200 (routes.ts sends stale links to the front page)`)
  }

  console.log('\narchive documents that exist — served as themselves')
  for (const p of PRESENT) {
    const res = await fetch(base + p)
    const type = res.headers.get('content-type') || ''
    console.log(`  ${String(res.status).padEnd(4)} ${p.padEnd(38)} ${type.split(';')[0]}`)
    if (res.status !== 200) fails.push(`${p}: status ${res.status}, expected 200`)
    else if (type.includes('text/html')) fails.push(`${p}: served as HTML — that is the app shell, not the file`)
  }

  // /data/model.json is the endpoint llms.txt and the page comment both point agents at,
  // and it is published by scripts/build_agent_endpoints.py -- a DIFFERENT script from
  // model/export.py, which writes the copy the app itself renders from. Forget the second
  // script and the app is right while the endpoint agents read is stale. That happened, and
  // it shipped to production, so it is checked rather than remembered.
  console.log('\npublished endpoint must match the model the app renders from')
  {
    const local = await readFile(join(APP, 'src', 'data', 'model.json'))
    const res = await fetch(base + '/data/model.json')
    const served = Buffer.from(await res.arrayBuffer())
    const h = (b) => createHash('sha256').update(b).digest('hex').slice(0, 12)
    const same = h(local) === h(served)
    console.log(`  ${same ? ' ok ' : 'FAIL'} /data/model.json  served ${h(served)}  ` +
      `app ${h(local)}  (${served.length.toLocaleString()} vs ${local.length.toLocaleString()} bytes)`)
    if (!same) {
      fails.push('/data/model.json is stale — run `python3 scripts/build_agent_endpoints.py` ' +
        'after model/export.py, or agents read different figures from the ones the site shows')
    }
  }

  // model/releases.py says in its own docstring that CURRENT "has to match the git tag
  // actually deployed". Nothing enforced that, so v4 and v5 both shipped while the footer
  // still read v3 -- the site telling returning readers it was a build from two deploys
  // ago. Checked here because it is the one version string a reader actually sees.
  console.log('\nthe version the site shows must be the tag that was deployed')
  {
    const model = JSON.parse(await readFile(join(APP, 'src', 'data', 'model.json'), 'utf8'))
    const shown = model.releases?.current ?? null
    // `git describe --abbrev=0` returns the nearest tag REACHABLE from HEAD, which is not
    // the same as HEAD being that tag. Production once ran three commits past v5 while
    // calling itself v5, and comparing names alone said that was fine. Compare commits.
    let tagged = null, atTag = true
    try {
      tagged = execFileSync('git', ['describe', '--tags', '--abbrev=0'],
        { cwd: APP, encoding: 'utf8' }).trim()
      const head = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: APP, encoding: 'utf8' }).trim()
      const tip = execFileSync('git', ['rev-list', '-n', '1', tagged],
        { cwd: APP, encoding: 'utf8' }).trim()
      atTag = head === tip
    } catch { /* not a checkout, or no tags */ }
    if (!shown) {
      console.log('  note  the model carries no release tag; nothing to compare')
    } else if (!tagged) {
      console.log(`  note  site shows ${shown}; no git tag found to compare against`)
    } else {
      const ok = shown === tagged && atTag
      console.log(`  ${ok ? ' ok ' : 'FAIL'} site shows ${shown}, newest git tag is ${tagged}` +
        `${atTag ? '' : ' — and HEAD is PAST that tag'}`)
      if (shown !== tagged) {
        fails.push(`the site shows ${shown} but the newest git tag is ${tagged} — add a ` +
          'release note in model/releases.py, or the footer tells readers this is an older build')
      } else if (!atTag) {
        fails.push(`HEAD is past ${tagged}, so this build ships changes the tag does not ` +
          'cover — add a release note and move the tag before deploying')
      }
    }
  }

  console.log('\narchive documents that do not exist — must 404, not 200')
  for (const p of ABSENT) {
    const res = await fetch(base + p)
    console.log(`  ${String(res.status).padEnd(4)} ${p}`)
    if (res.status !== 404) {
      fails.push(`${p}: status ${res.status}, expected 404. A missing document answering ` +
        '200 is indistinguishable from one that is there.')
    }
  }

  if (wrangler) wrangler.kill()

  if (fails.length) {
    console.error(`\n${fails.length} problem(s):`)
    for (const f of fails) console.error(`  - ${f}`)
    process.exit(1)
  }
  console.log('\nevery route serves its own content, stale links still land, and a missing ' +
    'document says so.')
}

main().catch(e => { console.error(e); process.exit(1) })
