#!/usr/bin/env node
// FETCH THE PUBLISHER'S OWN BYTES THROUGH A REAL BROWSER, for a site that refuses anything else.
//
//   node scripts/browser_fetch.mjs <outdir> <origin-page> <url> [<url> ...]
//
// mass.gov answers curl, urllib and every header set tried with `403 Not allowed`, and answers
// Chrome. So Chrome opens one page on the site (the origin page), and every URL is then fetched
// from INSIDE that page with `fetch()`. What is saved is the HTTP response body exactly as the
// server sent it -- not the rendered DOM, which would be our rendering of their document
// (CLAUDE.md rule 13). Content-Disposition is kept, because it carries the publisher's own
// filename for a download (rule 12). Writes <outdir>/<n>.bin per URL and <outdir>/result.json describing each:
// the requested URL, the final URL after redirects, the status and the content type.
import { spawn } from 'node:child_process'
import { mkdtemp, writeFile, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const CHROME = process.env.CHROME ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const [outdir, origin, ...urls] = process.argv.slice(2)
if (!outdir || !origin || !urls.length) {
  console.error('usage: browser_fetch.mjs <outdir> <origin-page> <url>...'); process.exit(2)
}
await mkdir(outdir, { recursive: true })
const profile = await mkdtemp(join(tmpdir(), 'bf-'))
const port = 9300 + Math.floor(Math.random() * 500)
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', `--user-data-dir=${profile}`,
  `--remote-debugging-port=${port}`, 'about:blank'], { stdio: 'ignore' })
const sleep = ms => new Promise(r => setTimeout(r, ms))
let target
for (let i = 0; i < 60 && !target; i++) {
  await sleep(250)
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
    target = list.find(t => t.type === 'page')
  } catch {}
}
if (!target) { chrome.kill(); throw new Error('Chrome did not start') }
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise(r => ws.addEventListener('open', r))
let id = 0; const waiting = new Map()
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data)
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id) }
})
const send = (method, params = {}) => new Promise(r => {
  const n = ++id; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params }))
})
await send('Page.enable')
await send('Page.navigate', { url: origin })
await sleep(8000)
const results = []
for (const [i, url] of urls.entries()) {
  const expr = `(async () => {
    const r = await fetch(${JSON.stringify(url)}, {credentials: 'include'});
    const b = new Uint8Array(await r.arrayBuffer());
    let s = ''; for (let j = 0; j < b.length; j += 0x8000) s += String.fromCharCode.apply(null, b.subarray(j, j + 0x8000));
    return JSON.stringify({status: r.status, url: r.url, type: r.headers.get('content-type'), disposition: r.headers.get('content-disposition'), b64: btoa(s)});
  })()`
  // One URL may not hang the run: a fetch that has not answered in 90 seconds is recorded
  // as an error and the next URL is tried.
  const m = await Promise.race([
    send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }),
    sleep(90000).then(() => ({ result: { exceptionDetails: 'timed out after 90s' } })),
  ])
  console.error(`  ${i + 1}/${urls.length} ${url}`)
  const v = m.result?.result?.value
  if (!v) { results.push({ requested: url, error: JSON.stringify(m.result?.exceptionDetails || m).slice(0, 300) }); continue }
  const o = JSON.parse(v)
  const file = join(outdir, `${i}.bin`)
  await writeFile(file, Buffer.from(o.b64, 'base64'))
  results.push({ requested: url, final: o.url, status: o.status, type: o.type, disposition: o.disposition, file })
  await sleep(1500)
}
await writeFile(join(outdir, 'result.json'), JSON.stringify(results, null, 2))
ws.close(); chrome.kill()
console.log(JSON.stringify(results.map(r => [r.status, r.type, r.requested]), null, 0))
