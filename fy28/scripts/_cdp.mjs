/**
 * A very small Chrome DevTools Protocol client, over Node 22's built-in WebSocket.
 *
 * Shared by check-interactive.mjs and compare-experience.mjs so there is one place where
 * "talk to Chrome" is defined. Deliberately not Puppeteer: the whole point of the
 * prerender toolchain here is that it adds nothing to package.json, and this is the only
 * part of it that needs more than `--dump-dom`.
 *
 * Needs Node 22:  source ~/.nvm/nvm.sh && nvm use 22
 */
import { spawn } from 'node:child_process'
import { mkdtemp } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

export const CHROME = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
].filter(Boolean).find(p => existsSync(p))

export const sleep = (ms) => new Promise(r => setTimeout(r, ms))

export class CDP {
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

/** Launch headless Chrome and return { proc, wsUrl, newPage() }. */
export async function launch(port) {
  if (typeof WebSocket === 'undefined') {
    throw new Error('needs Node 22+ for global WebSocket: source ~/.nvm/nvm.sh && nvm use 22')
  }
  if (!CHROME) throw new Error('no Chrome found; set CHROME=/path/to/chrome')
  const profile = await mkdtemp(join(tmpdir(), 'cdp-'))
  const proc = spawn(CHROME, [
    '--headless', '--disable-gpu', '--no-sandbox', '--no-first-run', '--hide-scrollbars',
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: 'ignore' })

  let wsUrl
  for (let i = 0; i < 60 && !wsUrl; i++) {
    await sleep(250)
    try {
      wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json())
        .webSocketDebuggerUrl
    } catch { /* still starting */ }
  }
  if (!wsUrl) { proc.kill(); throw new Error('chrome never exposed CDP') }

  const browser = await CDP.attach(wsUrl)
  return {
    proc,
    async newPage() {
      const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' })
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
      const page = await CDP.attach(list.find(t => t.id === targetId).webSocketDebuggerUrl)
      await page.send('Page.enable')
      await page.send('Runtime.enable')
      return page
    },
  }
}
