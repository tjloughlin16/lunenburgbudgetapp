// EVERY UNIT, AS A CITIZEN SEES IT — read out of the RENDERED HTML, not the payload.
//
//     node scripts/check_org_html.mjs [--limit N] [--unit NAME]
//
// TJ, 22 September 2026, with a screenshot of the Fire Chief filed under `MEMBERS, SEATS
// AND STAFF` below his own deputy: *"is the org chart updated?! There's NO way i still
// see this"*, and then: *"can you validate via the HTML for all 'units' (depts)? You need
// to make sure it works from citizen perspective."*
//
// He is right that this is the only validation that counts. `check_org_charts.py` asserts
// the MODEL, and every one of its checks passed while that screenshot was true — because
// the defect was `r.tier || '3'` in the page. The integer 0 is falsy in JavaScript, so
// every head in the archive was read as missing and filed with the staff. A model that is
// right and a page that renders it wrongly are indistinguishable from the model.
//
// So this renders each unit at its own address and reads the BANDS OUT OF THE HTML.
//
// WHAT IT ASSERTS, and each is a thing a resident would notice in a second:
//   - the bands come in order, heads first, and each appears at most once
//   - nobody whose printed title says they run the body sits below somebody who does not
//   - the top band is not occupied only by a deputy
//   - the body's own name is on its page, and the page is not empty
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { join, extname } from 'node:path'
import { readFile } from 'node:fs/promises'

const exec = promisify(execFile)
const DIST = join(process.cwd(), 'dist')
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const SEP = String.fromCharCode(1)

const BANDS = ['HEADS THE BODY', 'DEPUTY AND ASSISTANT',
  'SUPERVISORS, RANKED POSTS AND THE CLERK', 'MEMBERS, SEATS AND STAFF',
  'ASSOCIATE, HONORARY, EX OFFICIO AND NON-VOTING']
// A printed title that says its holder RUNS the body.
//
// A HIGHWAY SUPERINTENDENT IS NOT THE SUPERINTENDENT -- the same trap the builder had to
// solve, and this reader walked straight into it: the DPW's Cemetery and Highway
// Superintendents are heads of a DIVISION, under the Director who heads the department,
// and matching the bare word reported the department as upside down when it is right.
// A PRINCIPAL CLERK IS NOT A PRINCIPAL — the builder learned that hours ago and this
// reader did not, because the rule for `what counts as a head` lives in two files and
// they drift. Same class as the Cemetery Superintendent it also walked into. The honest
// fix is to publish the ladder from the builder and have the checker read it; until that
// exists, the exception is written in both places and this comment is the reason why.
const HEAD = /(^|\s)(chief of department|chief|superintendent|principal(?!\s+clerk)|town manager|chair(man|person|woman)?|library director)\b/i
const DIVISION = /\b(cemetery|highway|street|water|sewer|building|grounds|facilities)\s+superintendent\b/i
// A printed title that says its holder is SECOND.
const SECOND = /\b(deputy|assistant|asst\.?|vice[- ]?chair|lieutenant|lt\.?|sergeant|sgt\.?|interim|acting)\b/i

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.txt': 'text/plain',
  '.csv': 'text/csv', '.xml': 'application/xml', '.png': 'image/png',
  '.woff2': 'font/woff2', '.ico': 'image/x-icon',
}

function serve() {
  const s = createServer(async (req, res) => {
    const path = decodeURIComponent(req.url.split('?')[0])
    for (const p of [path, path + '.html', join(path, 'index.html'), '/index.html']) {
      try {
        const body = await readFile(join(DIST, p))
        res.writeHead(200, { 'content-type': MIME[extname(p)] ?? 'application/octet-stream' })
        return res.end(body)
      } catch { /* try the next candidate */ }
    }
    res.writeHead(404)
    res.end('not found')
  })
  return new Promise(r => s.listen(0, () => r([s, s.address().port])))
}

/** Just the chart, split into the blocks the page draws — one per building.
 *
 *  TWO THINGS THE FIRST VERSION GOT WRONG, and both were the reader's fault rather than
 *  the page's. It read the whole document, so the explanatory prose at the foot ("the
 *  town's officials listing marked its chairs...") came back as rows of the last band and
 *  every department failed. And it flattened the per-building sections, so Lunenburg
 *  Public Schools -- which correctly draws a head band for each of its four schools --
 *  looked like a page with four duplicate bands in the wrong order.
 */
// A body drawn a shift at a time has no band headings at all -- its structure is the
// shift, and the rank is the order inside it. Reading it with the band parser finds
// nothing, which is not the same as rendering nothing, so the caller checks the layout
// the payload declares before deciding what absence means.
function blocks(html) {
  // THE PAGE MARKS ITS OWN CHART: `<div data-org-chart>` wraps it, and everything outside
  // that -- the controls, the trend, the key, the caveats -- is not the chart.
  //
  // This used to find the end by searching for `What this report counts`, the `Grain`
  // component's own heading, and that is a positional name (rule 13b). The moment `Grain`
  // was reused for a chart caption ABOVE the chart, this truncated the page to nothing and
  // reported `no bands rendered at all` for 51 of 63 bodies. Every one was fine. A reader
  // that locates a section by a string living inside a component breaks whenever anybody
  // reuses that component, and it breaks by reporting defects in the DATA.
  //
  // The fallback keeps the old behaviour so a page that has not declared the marker still
  // reads, rather than silently checking nothing -- but it says so, because a checker that
  // quietly stops checking is worse than one that fails.
  let chart = html
  const open = html.indexOf('data-org-chart')
  if (open !== -1) {
    const from = html.lastIndexOf('<div', open)
    let depth = 0
    const re = /<(\/?)div\b[^>]*>/g
    re.lastIndex = from
    let m
    while ((m = re.exec(html))) {
      depth += m[1] ? -1 : 1
      if (depth === 0) { chart = html.slice(from, m.index + m[0].length); break }
    }
  } else {
    const end = html.indexOf('What this report counts')
    chart = end === -1 ? html : html.slice(0, end)
    console.log('  note: the page declares no data-org-chart marker; '
      + 'falling back to the old heading search')
  }
  // ...AND IT BEGINS AFTER THE WARNING CARDS. `This chart is not complete` quotes the
  // town's own sentence about how many people a body had, and that sentence contains the
  // word `heads` often enough to be read as a chart row — the reader reported the
  // Assessing office as having a head below its own head band, out of a caption.
  for (const card of ['This chart is not complete', 'is the town’s own staff directory']) {
    const at = chart.indexOf(card)
    if (at !== -1) {
      const close = chart.indexOf('</div>', chart.indexOf('</p>', at))
      if (close !== -1) chart = chart.slice(0, at) + chart.slice(close)
    }
  }
  const parts = chart.split(/<section\b/i).slice(1)
  return (parts.length ? parts : [chart]).map(parse).filter(b => b.length)
}

/** The bands and their rows, read back out of one block's markup. */
function parse(html) {
  const cells = html.replace(/<[^>]+>/g, SEP).replace(/&[a-z]+;/g, ' ')
    .split(SEP).map(t => t.trim()).filter(Boolean)
  const out = []
  let band = null
  for (const cell of cells) {
    const hit = BANDS.find(b => cell.toUpperCase() === b)
    if (hit) {
      band = { band: hit, rows: [] }
      out.push(band)
      continue
    }
    if (band && !/^\d+$/.test(cell)) band.rows.push(cell)
  }
  return out
}

async function main() {
  const payload = JSON.parse(readFileSync(join(DIST, 'data/org-charts.json'), 'utf8'))
  const args = process.argv.slice(2)
  const only = args.includes('--unit') ? args[args.indexOf('--unit') + 1] : null
  const limit = args.includes('--limit') ? Number(args[args.indexOf('--limit') + 1]) : 0
  let units = payload.units.filter(u => !only || u.unit === only)
  if (limit) units = units.slice(0, limit)

  const [server, port] = await serve()
  const problems = []
  let checked = 0
  for (const u of units) {
    const fy = u.years[u.years.length - 1]
    const url = `http://localhost:${port}/org-charts?unit=${encodeURIComponent(u.unit)}&fy=${fy}`
    let html
    try {
      ({ stdout: html } = await exec(CHROME, ['--headless', '--disable-gpu', '--no-sandbox',
        '--virtual-time-budget=8000', '--dump-dom', url],
      { maxBuffer: 64 * 1024 * 1024, timeout: 120_000, killSignal: 'SIGKILL' }))
    } catch (e) {
      problems.push(`${u.unit}: chrome failed — ${String(e.message).slice(0, 70)}`)
      continue
    }
    checked++
    const body = html.slice(html.indexOf('people named'),
      html.indexOf('What this report counts'))
    const names = body.replace(/<[^>]+>/g, SEP).split(SEP)
      .map(t => t.trim()).filter(Boolean)
    // A ONE-PERSON BODY RENDERS ONE NAME AND NO BAND LABEL, by design — so `fewer than
    // two strings` is what a correct one-person chart looks like, not an empty one. The
    // Town Forest Committee has a single member in FY2020 and was reported as blank.
    const people = payload.rows.filter(r => r.unit === u.unit && r.fy === fy
      && r.person.trim()).length
    if (names.length < Math.min(2, people)) {
      problems.push(`${u.unit} FY${fy}: the chart is empty`)
      continue
    }
    if (u.layout === 'shifts') {
      // The head must be the first person on the page, above every shift.
      const first = names.find(n => HEAD.test(n) || SECOND.test(n))
      if (first && SECOND.test(first) && !HEAD.test(first))
        problems.push(`${u.unit} FY${fy}: a second-in-command is the first name shown `
          + `— ${first.slice(0, 40)}`)
      continue
    }
    if (!blocks(html).length) {
      problems.push(`${u.unit} FY${fy}: no bands rendered at all`)
      continue
    }
    // `&` reaches the DOM as `&amp;`, so `Inspector Of Weights & Measures` was reported
    // missing from its own page. Compare text to text, never text to markup.
    const flat = html.replace(/<[^>]+>/g, ' ')
      .replace(/&amp;/g, '&').replace(/&#039;|&apos;/g, "'").replace(/&quot;/g, '"')
    if (!flat.includes(u.unit.replace(/ \(.*\)$/, '')))
      problems.push(`${u.unit}: the body's own name is not on its page`)

    for (const bands of blocks(html)) {
      const seen = bands.map(b => b.band)
      const dupes = [...new Set(seen.filter((b, i) => seen.indexOf(b) !== i))]
      if (dupes.length)
        problems.push(`${u.unit} FY${fy}: band rendered twice — ${dupes.join(', ')}`)

      const order = seen.map(b => BANDS.indexOf(b))
      if (order.some((v, i) => i && v < order[i - 1]))
        problems.push(`${u.unit} FY${fy}: bands out of order — ${seen.join(' | ')}`)

      const top = bands[0]
      const below = bands.slice(1).flatMap(b => b.rows)
      const headBelow = below.filter(r => HEAD.test(r) && !SECOND.test(r)
        && !DIVISION.test(r))
      if (headBelow.length)
        problems.push(`${u.unit} FY${fy}: "${headBelow[0].slice(0, 44)}" runs the body `
          + `and sits below "${top.band.toLowerCase()}"`)
      if (top.band === BANDS[0] && top.rows.length && top.rows.every(r => SECOND.test(r)))
        problems.push(`${u.unit} FY${fy}: the top band holds only a second-in-command `
          + `— ${top.rows[0].slice(0, 40)}`)
    }
  }
  server.close()

  console.log(`${checked} of ${units.length} units rendered and read from HTML`)
  if (problems.length) {
    console.error(`\n${problems.length} problem(s) a reader would see:`)
    for (const p of problems) console.error('  - ' + p)
    process.exit(1)
  }
  console.log('every unit: heads first, bands in order and each once, nobody above their chief.')
}

main().catch(e => { console.error(e); process.exit(1) })
