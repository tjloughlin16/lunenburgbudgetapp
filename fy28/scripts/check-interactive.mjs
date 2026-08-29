/**
 * Prove the prerendered build is still the app.
 *
 * `prerender.mjs` writes rendered HTML into `dist/<slug>/index.html`. The obvious worry is
 * that it turns a working application into a photograph of one. This checks that it does
 * not, on the real built output, by driving Chrome rather than by reasoning about React.
 *
 * Comparing the DOM before and after JavaScript is NOT sufficient and was the first thing
 * tried: the settled DOM is identical either way, so a page where React never booted scores
 * exactly the same as one where it did. The check has to look for React itself and then
 * make the page do something.
 *
 * Three assertions per route, each of which fails differently:
 *
 *   1. **React attached.** React 18 stamps its container with a `__reactContainer$…` key.
 *      Present means `createRoot` ran and adopted the element. Absent means the page is a
 *      photograph — the exact failure this script exists to catch.
 *   2. **React replaced the prerendered markup.** Every child of `#root` is stamped
 *      during HTML parsing, before the deferred module script runs. If those stamps are
 *      gone afterwards and the page is still full, React tore the static markup out and
 *      rendered its own — which is what `createRoot` (as opposed to `hydrateRoot`) does,
 *      and is why prerendering cannot desynchronise this app. Reading React's internal
 *      fibers was tried first and gave false negatives on three routes: under StrictMode
 *      the fiber's `child` is null on whichever alternate you happen to catch.
 *   3. **It responds.** Click a real control and require the DOM to change. This is the
 *      only one that tests the thing a visitor cares about.
 *
 *     node scripts/check-interactive.mjs        # after build + prerender
 *
 * Needs Node 22 (global WebSocket, used to speak CDP without a dependency):
 *     source ~/.nvm/nvm.sh && nvm use 22
 */
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { readFile, stat, mkdtemp } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, extname, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const DIST = join(HERE, '..', 'dist')
const PORT = 8796
const CDP_PORT = 9333

const CHROME = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
].filter(Boolean).find(p => existsSync(p))

// One page per kind of interactivity the site has, rather than all fourteen: a drill-in
// with disclosures, the two scenario builders, and the front door.
const ROUTES = ['/', '/athletics', '/build-your-own-budget', '/priorities', '/bend-the-curve']

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.csv': 'text/csv', '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml', '.md': 'text/markdown',
}

function serve() {
  return createServer(async (req, res) => {
    const p = decodeURIComponent(new URL(req.url, 'http://x').pathname)
    const flat = p === '/' ? join(DIST, 'index.html') : join(DIST, `${p}.html`)
    for (const cand of [join(DIST, p), flat, join(DIST, p, 'index.html')]) {
      try {
        if ((await stat(cand)).isFile()) {
          res.writeHead(200, { 'content-type': MIME[extname(cand)] ?? 'application/octet-stream' })
          return res.end(await readFile(cand))
        }
      } catch { /* try the next candidate */ }
    }
    // Deliberately a real 404: this server mirrors the fixed host behaviour, so a route
    // that only works via the SPA fallback shows up here as a failure rather than passing.
    res.writeHead(404, { 'content-type': 'text/plain' })
    res.end('not found')
  })
}

/** Minimal CDP client over Node's built-in WebSocket. */
class CDP {
  #ws; #id = 0; #pending = new Map()
  static async attach(wsUrl) {
    const c = new CDP()
    c.#ws = new WebSocket(wsUrl)
    await new Promise((ok, no) => { c.#ws.onopen = ok; c.#ws.onerror = no })
    c.#ws.onmessage = (e) => {
      const m = JSON.parse(e.data)
      const p = c.#pending.get(m.id)
      if (p) { c.#pending.delete(m.id); m.error ? p.no(new Error(m.error.message)) : p.ok(m.result) }
    }
    return c
  }
  send(method, params = {}) {
    const id = ++this.#id
    this.#ws.send(JSON.stringify({ id, method, params }))
    return new Promise((ok, no) => this.#pending.set(id, { ok, no }))
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', {
      expression, returnByValue: true, awaitPromise: true,
    })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text)
    return r.result.value
  }
  close() { this.#ws.close() }
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

async function main() {
  if (typeof WebSocket === 'undefined') {
    console.error('needs Node 22+ for global WebSocket:  source ~/.nvm/nvm.sh && nvm use 22')
    process.exit(1)
  }
  if (!CHROME) { console.error('no Chrome found; set CHROME='); process.exit(1) }
  if (!existsSync(join(DIST, 'index.html'))) {
    console.error('no dist/ — run npm run build && node scripts/prerender.mjs')
    process.exit(1)
  }

  const server = serve()
  await new Promise(r => server.listen(PORT, r))

  const profile = await mkdtemp(join(tmpdir(), 'prerender-check-'))
  const chrome = spawn(CHROME, [
    '--headless', '--disable-gpu', '--no-sandbox', '--no-first-run',
    `--remote-debugging-port=${CDP_PORT}`, `--user-data-dir=${profile}`,
    'about:blank',
  ], { stdio: 'ignore' })

  let wsUrl
  for (let i = 0; i < 60 && !wsUrl; i++) {
    await sleep(250)
    try {
      const r = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`)
      wsUrl = (await r.json()).webSocketDebuggerUrl
    } catch { /* chrome still starting */ }
  }
  if (!wsUrl) { chrome.kill(); server.close(); throw new Error('chrome never exposed CDP') }

  const failures = []
  const rows = []

  for (const route of ROUTES) {
    const target = await (await CDP.attach(wsUrl)).send('Target.createTarget', { url: 'about:blank' })
    const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json()
    const page = list.find(t => t.id === target.targetId)
    const cdp = await CDP.attach(page.webSocketDebuggerUrl)
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    // Stamp the prerendered nodes while the parser is still inserting them -- this runs at
    // document-start, and the app's module script is deferred, so the stamps are on before
    // React can exist.
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `
        window.__stamped = 0
        new MutationObserver((_, obs) => {
          const root = document.getElementById('root')
          if (root && root.children.length) {
            for (const c of root.children) c.setAttribute('data-prerendered', '1')
            window.__stamped = root.children.length
            obs.disconnect()
          }
        }).observe(document, { childList: true, subtree: true })
      `,
    })
    await cdp.send('Page.navigate', { url: `http://localhost:${PORT}${route}` })

    // Wait for the app to settle rather than for a fixed time.
    let ready = false
    for (let i = 0; i < 40 && !ready; i++) {
      await sleep(250)
      try {
        ready = await cdp.eval(
          `!!document.getElementById('root') &&
           Object.keys(document.getElementById('root')).some(k => k.startsWith('__reactContainer'))`)
      } catch { /* navigation in flight */ }
    }

    const reactAttached = ready
    const replaced = reactAttached && await cdp.eval(`(() => {
      const root = document.getElementById('root')
      if (!window.__stamped) return 'no-prerender'          // nothing static was served
      const left = root.querySelectorAll('[data-prerendered]').length
      return left === 0 && root.childElementCount > 0
    })()`)

    // Click the first control that is a real in-page button, then require a change.
    const responded = reactAttached && await cdp.eval(`(async () => {
      const before = document.body.innerText
      const btns = [...document.querySelectorAll('button')]
        .filter(b => !b.disabled && b.offsetParent !== null)
      if (!btns.length) return 'no-buttons'
      for (const b of btns.slice(0, 12)) {
        b.click()
        await new Promise(r => setTimeout(r, 220))
        if (document.body.innerText !== before) return true
      }
      return false
    })()`)

    if (!reactAttached) failures.push(`${route}: React never attached — page is a photograph`)
    else if (replaced === 'no-prerender') failures.push(`${route}: served no prerendered markup`)
    else if (!replaced) failures.push(`${route}: prerendered nodes survived — React did not `
      + 'take over, so what a visitor sees is the snapshot, not the app')
    else if (responded === 'no-buttons') failures.push(`${route}: no clickable control found to test`)
    else if (!responded) failures.push(`${route}: clicked 12 controls and the DOM never changed`)

    rows.push({ route, reactAttached, replaced, responded })
    await cdp.send('Page.close').catch(() => {})
    cdp.close()
  }

  chrome.kill()
  server.close()

  const pad = Math.max(...ROUTES.map(r => r.length))
  console.log(`${'route'.padEnd(pad)}   react   replaced static   responds to a click`)
  for (const r of rows) {
    const y = (v) => (v === true ? '  yes' : (v === 'no-buttons' || v === 'no-prerender') ? ' none' : '   NO')
    console.log(`${r.route.padEnd(pad)}  ${y(r.reactAttached)}          ${y(r.replaced)}` +
      `              ${y(r.responded)}`)
  }

  if (failures.length) {
    console.error(`\n${failures.length} problem(s):`)
    for (const f of failures) console.error(`  - ${f}`)
    process.exit(1)
  }
  console.log('\nprerendered pages boot React, replace the static markup, and respond to input.')
}

main().catch(e => { console.error(e); process.exit(1) })
