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
  return [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)].map(m => (m[2] ? `/${m[2]}` : '/'))
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
