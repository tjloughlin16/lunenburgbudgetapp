/**
 * Is the site, for a person with a browser, the same site it was before prerendering?
 *
 * The honest comparison is NOT staging against production: production is many commits
 * behind, so its content differs for reasons that have nothing to do with this change.
 * This builds the SAME commit two ways — plain (`dist-plain`, what shipped before) and
 * prerendered (`dist`) — and drives both in a real browser. The only difference between
 * them is the thing being tested.
 *
 * Four questions, in the order a user would notice them:
 *
 *   1. **Does the settled page look the same?** After JavaScript has run, the text a
 *      visitor reads and the DOM they interact with must be identical. If this differs at
 *      all, the migration changed the product.
 *   2. **Is there a flash of wrong content?** This is the real risk of prerendering, and
 *      the one worth measuring rather than reasoning about. The prerendered HTML paints
 *      before React boots. If what it paints differs from what React then renders, the
 *      user sees a flicker of stale or default content — the failure mode that makes
 *      prerendered apps feel broken. The page is sampled every 100ms from navigation so
 *      the sequence is visible, not assumed.
 *   3. **Do interactions behave the same?** The same controls are clicked in the same
 *      order on both builds and the resulting text compared.
 *   4. **Is it faster or slower?** First Contentful Paint on both. Prerendering should
 *      improve it; a regression would be a reason to stop.
 *
 * Screenshots of both builds are written to `scratch/experience/` for eyeballing.
 *
 *     node scripts/compare-experience.mjs
 *
 * Needs Node 22:  source ~/.nvm/nvm.sh && nvm use 22
 */
import { createServer } from 'node:http'
import { readFile, stat, mkdir, writeFile, rm, cp } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, extname, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { launch, sleep } from './_cdp.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const APP = join(HERE, '..')
const PRERENDERED = join(APP, 'dist')
const PLAIN = join(APP, 'dist-plain')
const SHOTS = join(APP, 'scratch', 'experience')

const PORT_PRE = 8810
const PORT_PLAIN = 8811
const CDP_PORT = 9345

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.csv': 'text/csv', '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml', '.md': 'text/markdown',
  '.woff2': 'font/woff2', '.png': 'image/png',
}

/** Serve a build the way the host does: real file, else <slug>.html, else the shell. */
function serve(root) {
  return createServer(async (req, res) => {
    const p = decodeURIComponent(new URL(req.url, 'http://x').pathname)
    const flat = p === '/' ? join(root, 'index.html') : join(root, `${p}.html`)
    for (const cand of [join(root, p), flat]) {
      try {
        if ((await stat(cand)).isFile()) {
          res.writeHead(200, { 'content-type': MIME[extname(cand)] ?? 'application/octet-stream' })
          return res.end(await readFile(cand))
        }
      } catch { /* next candidate */ }
    }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
    res.end(await readFile(join(root, 'index.html')))
  })
}

async function readRoutes() {
  const src = await readFile(join(APP, 'src', 'routes.ts'), 'utf8')
  const block = src.match(/export const SLUG: Record<Tab, string> = \{([\s\S]*?)\n\}/)
  return [...block[1].matchAll(/^\s*(\w+):\s*'([^']*)',/gm)].map(m => (m[2] ? `/${m[2]}` : '/'))
}

const SETTLED = `(() => {
  const r = document.getElementById('root')
  return r ? r.innerText.replace(/\\s+/g, ' ').trim() : ''
})()`

/** Load a route and record what the user sees, when, and what happens on a click. */
async function visit(browser, base, route, { shots, label }) {
  const page = await browser.newPage()
  await page.send('Performance.enable').catch(() => {})

  // Trace on every animation frame, installed before navigation. Polling from Node was
  // the first attempt and was too coarse to be fair: it sampled every 100ms and reported
  // "a flash of different content" for what turned out to be a single frame during
  // React's mount. Measure at frame resolution or do not make the claim.
  await page.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      window.__trace = []
      const t0 = performance.now()
      ;(function tick() {
        const r = document.getElementById('root')
        window.__trace.push([Math.round(performance.now() - t0),
          r ? r.innerText.replace(/\\s+/g, ' ').trim() : null])
        if (performance.now() - t0 < 2500) requestAnimationFrame(tick)
      })()
    `,
  })

  await page.send('Page.navigate', { url: base + route })
  await sleep(3200)

  let settled = ''
  for (let i = 0; i < 60; i++) {
    const t = await page.eval(SETTLED).catch(() => '')
    if (t && t === settled) break
    settled = t
    await sleep(200)
  }

  const trace = (await page.eval('window.__trace').catch(() => [])) || []

  const fcp = await page.eval(`(() => {
    const e = performance.getEntriesByName('first-contentful-paint')[0]
    return e ? Math.round(e.startTime) : null
  })()`).catch(() => null)

  const nodes = await page.eval('document.getElementsByTagName("*").length').catch(() => 0)

  // Click the same controls in the same order on both builds.
  const afterClicks = await page.eval(`(async () => {
    const btns = [...document.querySelectorAll('button')]
      .filter(b => !b.disabled && b.offsetParent !== null).slice(0, 5)
    for (const b of btns) { b.click(); await new Promise(r => setTimeout(r, 200)) }
    const r = document.getElementById('root')
    return { clicked: btns.length, text: r ? r.innerText.replace(/\\s+/g,' ').trim() : '' }
  })()`).catch(() => ({ clicked: 0, text: '' }))

  if (shots) {
    const slug = route === '/' ? 'root' : route.slice(1)
    const shot = await page.send('Page.captureScreenshot', { format: 'png' }).catch(() => null)
    if (shot) await writeFile(join(SHOTS, `${slug}.${label}.png`), Buffer.from(shot.data, 'base64'))
  }

  await page.send('Page.close').catch(() => {})
  page.close()
  // Frames where the page was painted but showed something other than the final content.
  const painted = trace.filter(([, t]) => t !== null && t !== '')
  const firstPaintedAt = painted.length ? painted[0][0] : null
  const wrong = painted.filter(([, t]) => t !== settled)
  const blank = trace.filter(([, t]) => t === '')
  const span = (fs) => (fs.length ? fs.at(-1)[0] - fs[0][0] : 0)

  return { settled, fcp, nodes, afterClicks, firstPaintedAt,
           wrongMs: span(wrong), wrongFrames: wrong.length,
           blankMs: span(blank), blankFrames: blank.length }
}

async function main() {
  if (!existsSync(join(PRERENDERED, 'index.html'))) {
    console.error('no dist/ — run `npm run build:site` first'); process.exit(1)
  }
  if (!existsSync(join(PLAIN, 'index.html'))) {
    console.error('no dist-plain/ — create it from the SAME build with:\n' +
      '  npm run build && cp -R dist dist-plain && node scripts/prerender.mjs')
    process.exit(1)
  }
  // Same bundle in both, or the comparison means nothing.
  const a = await readFile(join(PRERENDERED, 'index.html'), 'utf8')
  const b = await readFile(join(PLAIN, 'index.html'), 'utf8')
  // The build emits a relative src ("./assets/…"), not an absolute one.
  const asset = (s) => (s.match(/src="\.?\/?(assets\/index-[^"]+\.js)"/) || [])[1]
  if (!asset(a) || asset(a) !== asset(b)) {
    console.error(`dist and dist-plain are different builds (${asset(a)} vs ${asset(b)}).\n` +
      'Rebuild both from one `npm run build` or the comparison is meaningless.')
    process.exit(1)
  }

  await rm(SHOTS, { recursive: true, force: true })
  await mkdir(SHOTS, { recursive: true })

  const routes = await readRoutes()
  const sPre = serve(PRERENDERED); await new Promise(r => sPre.listen(PORT_PRE, r))
  const sPlain = serve(PLAIN); await new Promise(r => sPlain.listen(PORT_PLAIN, r))
  const browser = await launch(CDP_PORT)

  const fails = []
  const rows = []

  for (const route of routes) {
    const plain = await visit(browser, `http://127.0.0.1:${PORT_PLAIN}`, route,
      { shots: true, label: 'before' })
    const pre = await visit(browser, `http://127.0.0.1:${PORT_PRE}`, route,
      { shots: true, label: 'after' })

    const sameSettled = plain.settled === pre.settled
    const sameClicks = plain.afterClicks.text === pre.afterClicks.text

    // One frame at 60fps is ~17ms. A difference shorter than two frames is not something
    // a person sees; anything longer is, and is reported with its duration rather than as
    // a yes/no.
    const FRAME = 34
    const flashy = pre.wrongMs > FRAME || pre.blankMs > FRAME

    if (!sameSettled) {
      let i = 0
      while (i < Math.min(plain.settled.length, pre.settled.length)
             && plain.settled[i] === pre.settled[i]) i++
      fails.push(`${route}: settled content differs (${plain.settled.length} vs ` +
        `${pre.settled.length} chars, first at ${i})\n` +
        `      before: ${JSON.stringify(plain.settled.slice(Math.max(0, i - 50), i + 60))}\n` +
        `      after : ${JSON.stringify(pre.settled.slice(Math.max(0, i - 50), i + 60))}`)
    }
    if (!sameClicks) fails.push(`${route}: interaction result differs between builds`)
    if (flashy) {
      fails.push(`${route}: visible wrong/blank content for ${Math.max(pre.wrongMs, pre.blankMs)}ms`)
    }

    rows.push({ route, sameSettled, sameClicks, flashy,
      wrongMs: pre.wrongMs, blankMs: pre.blankMs,
      firstPaintPre: pre.firstPaintedAt, firstPaintPlain: plain.firstPaintedAt,
      fcpPre: pre.fcp, fcpPlain: plain.fcp })
  }

  browser.proc.kill(); sPre.close(); sPlain.close()

  const pad = Math.max(...routes.map(r => r.length))
  console.log(`${'route'.padEnd(pad)}  same page  same click  ` +
    `${'wrong/blank'.padStart(12)}  ${'content at'.padStart(11)}  ${'was'.padStart(7)}`)
  for (const r of rows) {
    const y = (v) => (v ? ' yes' : '  NO')
    const worst = Math.max(r.wrongMs, r.blankMs)
    console.log(`${r.route.padEnd(pad)}     ${y(r.sameSettled)}       ${y(r.sameClicks)}` +
      `  ${String(worst).padStart(10)}ms  ${String(r.firstPaintPre ?? '?').padStart(9)}ms` +
      `  ${String(r.firstPaintPlain ?? '?').padStart(5)}ms`)
  }

  const avg = (k) => Math.round(rows.reduce((s, r) => s + (r[k] ?? 0), 0) / rows.length)
  console.log(`\nmean first contentful paint : ${avg('fcpPlain')}ms before, ${avg('fcpPre')}ms after`)
  console.log(`mean content on screen at   : ${avg('firstPaintPlain')}ms before, ` +
    `${avg('firstPaintPre')}ms after`)
  console.log(`screenshots (before/after per route): ${SHOTS}`)

  if (fails.length) {
    console.error(`\n${fails.length} difference(s) a user could notice:`)
    for (const f of fails) console.error(`  - ${f}`)
    process.exit(1)
  }
  console.log('\nIdentical settled content and identical interaction results on every route, ' +
    'and no flash of pre-React content. For a user with a browser, nothing changed.')
}

main().catch(e => { console.error(e); process.exit(1) })
