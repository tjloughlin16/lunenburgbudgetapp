import { SITE } from './abs'

/** EVERY TABLE ON THE SITE, AS A FILE. TJ, 23 October 2026, right after sending a board member
 *  the reserve page: "We need a way for any table to be downloaded as a CSV or excel."
 *
 *  ONE MECHANISM. Every table reaches a file through `download()` here, whatever drew it:
 *
 *    - FigureTable (report.tsx) hands over its payload's views, exact, every tab;
 *    - VoteList and the presence matrix hand over the rows their payload holds;
 *    - every other <table> the site renders is read off the page by `gridFromTable()`, through
 *      the enhancer in TableDownload.tsx, which attaches the control once, app-wide.
 *
 *  VALUES, NOT DISPLAY STRINGS. A spreadsheet user wants numbers: "$1,234,567" -> 1234567 with
 *  the unit moved into the header, "12.3%" -> 12.3, a dash -> empty. A footnote mark on a
 *  number is not dropped; it moves to a Notes column, because a figure with a dagger is a
 *  different claim from one without (rule 3).
 *
 *  A FILE CARRIES ITS OWN ADDRESS (rules 3 and 12). Above the data: what the table is, which
 *  view, the page and its full address, the date it was downloaded, and the table's note.
 *  Below it (CSV) or on a sheet of its own (Excel): the page's sources. A table separated from
 *  the page it came from is otherwise a set of numbers nobody can check. */

export type Cell = string | null
export type Grid = {
  columns: string[]
  rows: Cell[][]
  /** The first column names the row ("FY2021*", a department): kept as text, always. */
  rowHeader?: boolean
}
export type ExportView = { label?: string; note?: string[]; grid: Grid }
export type ExportSpec = {
  caption: string
  views: ExportView[]
  /** The view on screen: the one a CSV holds. Excel holds every view, a sheet each. */
  current?: number
}
export type Source = { label: string; url: string }

/* ------------------------------------------------------------------ one cell's value */

type Parsed =
  | { k: 'empty' }
  | { k: 'text' }
  | { k: 'num'; n: number; unit: '$' | '%' | 'pp' | ''; marks: string; dp: number }

const MARKS = /[†‡§¶*]/g
const EMPTY = /^(?:[—–\-−]+|n\/?a|\.{3}|…)?$/i
const NUMBER = /^(\d{1,3}(?:,\d{3})+|\d+)?(\.\d+)?$/

export function parseCell(raw: Cell): Parsed {
  if (raw == null) return { k: 'empty' }
  const s = raw.replace(/[   ]/g, ' ').trim()
  if (EMPTY.test(s)) return { k: 'empty' }
  const marks = (s.match(MARKS) ?? []).join('')
  let t = s.replace(MARKS, '').trim()
  if (!t) return { k: 'text' }
  let neg = false
  if (/^\(.*\)$/.test(t)) { neg = true; t = t.slice(1, -1).trim() }
  const sign = () => {
    const m = /^([+\-−–])\s*/.exec(t)
    if (m) { if (m[1] !== '+') neg = !neg; t = t.slice(m[0].length) }
  }
  sign()
  let unit: '$' | '%' | 'pp' | '' = ''
  if (t.startsWith('$')) { unit = '$'; t = t.slice(1).trim(); sign() }
  let mult = 1
  const suf = /\s*(%|pp|pts?|points?|percentage points|[KkMB]|million|billion)$/.exec(t)
  if (suf) {
    const x = suf[1]
    if (x === '%') { if (unit) return { k: 'text' }; unit = '%' }
    else if (/^(pp|pts?|points?|percentage points)$/.test(x)) { if (unit) return { k: 'text' }; unit = 'pp' }
    else mult = /^[Kk]$/.test(x) ? 1e3 : /^(M|million)$/.test(x) ? 1e6 : 1e9
    t = t.slice(0, suf.index).trim()
  }
  if (!t || !NUMBER.test(t)) return { k: 'text' }
  const dp = (t.split('.')[1] ?? '').length
  let n = Number(t.replace(/,/g, '')) * mult
  if (!Number.isFinite(n)) return { k: 'text' }
  if (mult !== 1) n = Math.round(n * 1e6) / 1e6
  return { k: 'num', n: neg ? -n : n, unit, marks, dp: mult === 1 ? dp : 0 }
}

/* ------------------------------------------------------------------ a grid, as values */

export type Value = string | number | null
export type Typed = {
  columns: string[]
  rows: Value[][]
  /** Per column: how a number in it is written in Excel. */
  formats: (string | undefined)[]
}

const UNIT_HEADER: Record<string, string> = { '$': '$', '%': '%', 'pp': 'percentage points' }

/** A column is a number column when every filled cell in it reads as a number in ONE unit (a
 *  bare figure among dollar figures is a dollar figure: financial tables print the $ on the
 *  first row only). Anything else stays text, exactly as printed. */
export function typeGrid(g: Grid): Typed {
  const width = Math.max(g.columns.length, ...g.rows.map(r => r.length))
  const parsed = g.rows.map(r => Array.from({ length: width }, (_, i) => parseCell(r[i] ?? null)))
  const columns: string[] = []
  const formats: (string | undefined)[] = []
  const numeric: boolean[] = []
  for (let c = 0; c < width; c++) {
    const head = (g.columns[c] ?? '').trim()
    const cells = parsed.map(r => r[c])
    const nums = cells.filter(x => x.k === 'num') as Extract<Parsed, { k: 'num' }>[]
    const units = new Set(nums.map(x => x.unit).filter(Boolean))
    const ok = !(c === 0 && g.rowHeader) && nums.length > 0
      && cells.every(x => x.k !== 'text') && units.size <= 1
    numeric.push(ok)
    const unit = ok ? [...units][0] ?? '' : ''
    const tag = UNIT_HEADER[unit]
    const already = unit === '$' ? /\$|dollar/i.test(head) : unit === '%' ? /%|percent/i.test(head)
      : unit === 'pp' ? /point/i.test(head) : true
    columns.push(tag && !already ? `${head || 'Value'} (${tag})` : head || (c === 0 ? '' : `Column ${c + 1}`))
    const dp = Math.min(4, Math.max(0, ...nums.map(x => x.dp)))
    formats.push(ok ? (unit === '$' || Math.max(...nums.map(x => Math.abs(x.n))) >= 1000
      ? `#,##0${dp ? '.' + '0'.repeat(dp) : ''}` : dp ? `0.${'0'.repeat(dp)}` : '0') : undefined)
  }
  const anyMarks = parsed.some(r => r.some((x, c) => numeric[c] && x.k === 'num' && x.marks))
  const rows: Value[][] = parsed.map((r, j) => {
    const out: Value[] = r.map((x, c) => {
      const raw = g.rows[j][c] ?? null
      if (x.k === 'empty') return null
      if (numeric[c] && x.k === 'num') return x.n
      return raw == null ? null : raw.replace(/\s+/g, ' ').trim()
    })
    if (anyMarks) {
      out.push(r.map((x, c) => numeric[c] && x.k === 'num' && x.marks
        ? `${columns[c] || 'Value'}: ${x.marks}` : '').filter(Boolean).join('; ') || null)
    }
    return out
  })
  if (anyMarks) { columns.push('Notes (marks printed beside a figure)'); formats.push(undefined) }
  return { columns, rows, formats }
}

/* ------------------------------------------------------------------ read a <table> off the page */

const SKIP = '[aria-hidden="true"], .sr-only, .tbl-dl, button, svg, script, style'

/** A cell's text as a reader sees it: what is drawn only for the eye (aria-hidden arrows) and
 *  what is said only to a screen reader (sr-only) both left out, and a line set in its own block
 *  (a code under a name) kept apart from its neighbour by a space. */
export function cellText(el: Element): string {
  const parts: string[] = []
  let last: Element | null = null
  const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    const p = n.parentElement
    if (!p || p.closest(SKIP) && el.contains(p.closest(SKIP))) continue
    const text = n.nodeValue ?? ''
    if (last && p !== last && parts.length) parts.push(' ')
    parts.push(text)
    last = p
  }
  return parts.join('').replace(/\s+/g, ' ').trim()
}

/** A table's cells as a rectangle, with colspan and rowspan laid out so a column stays a column. */
function expand(rows: HTMLTableRowElement[]): { text: string; th: boolean }[][] {
  const out: { text: string; th: boolean }[][] = []
  rows.forEach((tr, y) => {
    out[y] ??= []
    let x = 0
    for (const td of Array.from(tr.cells)) {
      while (out[y][x]) x++
      const text = cellText(td)
      const cs = Math.max(1, td.colSpan || 1), rs = Math.max(1, td.rowSpan || 1)
      for (let dy = 0; dy < rs && y + dy < rows.length; dy++) {
        out[y + dy] ??= []
        for (let dx = 0; dx < cs; dx++) out[y + dy][x + dx] = { text: dx === 0 && dy === 0 ? text : (dy === 0 ? '' : text), th: td.tagName === 'TH' }
      }
      x += cs
    }
  })
  const w = Math.max(0, ...out.map(r => r.length))
  return out.map(r => Array.from({ length: w }, (_, i) => r[i] ?? { text: '', th: false }))
}

export function gridFromTable(t: HTMLTableElement): Grid {
  const all = Array.from(t.rows).filter(r => !r.closest(SKIP) || !t.contains(r.closest(SKIP)))
  let head = all.filter(r => r.parentElement?.tagName === 'THEAD')
  let body = all.filter(r => r.parentElement?.tagName !== 'THEAD' && r.parentElement?.tagName !== 'TFOOT')
  const foot = all.filter(r => r.parentElement?.tagName === 'TFOOT')
  if (!head.length && body.length && Array.from(body[0].cells).every(c => c.tagName === 'TH')) {
    head = [body[0]]; body = body.slice(1)
  }
  const h = expand(head)
  const b = expand([...body, ...foot])
  const width = Math.max(h[0]?.length ?? 0, b[0]?.length ?? 0)
  const columns = Array.from({ length: width }, (_, i) => {
    const seen: string[] = []
    for (const r of h) { const s = r[i]?.text; if (s && !seen.includes(s)) seen.push(s) }
    return seen.join(' – ')
  })
  // A row whose only filled cell spans the table is a group heading inside the body. It is kept,
  // as a row with its label in the first column, so the rows under it still say what they are.
  const rows = b.map(r => Array.from({ length: width }, (_, i) => r[i]?.text || null))
  const rowHeader = b.length > 0 && b.every(r => r[0]?.th || !r[0]?.text)
  return { columns, rows, rowHeader }
}

/* ------------------------------------------------------------------ what the table is, and where it came from */

export function tableCaption(t: HTMLTableElement): string {
  const own = t.caption ? cellText(t.caption) : ''
  if (own) return own
  const fig = t.closest('figure')?.querySelector('figcaption')
  if (fig) return cellText(fig)
  const aria = t.getAttribute('aria-label') || t.dataset.caption
  if (aria) return aria
  // The nearest heading above the table, in reading order.
  const hs = Array.from(document.querySelectorAll('main h1, main h2, main h3, main h4, h1, h2, h3, h4'))
  let best: Element | null = null
  for (const h of hs) if (h.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING) best = h
  return best ? cellText(best) : ''
}

/** The page's sources, read where the page prints them: any block marked `data-page-sources`
 *  (Provenance in report.tsx, Sources on a topic page), else the links under a heading that
 *  says "Sources". One reader, so every table on a page carries the same list. */
export function pageSources(): Source[] {
  const out: Source[] = []
  const seen = new Set<string>()
  const add = (a: HTMLAnchorElement) => {
    // An in-app link resolves against wherever the page is being read (a dev server, the
    // prerenderer); the file names the site's own address instead.
    let url = a.href
    try {
      const u = new URL(a.href, window.location.href)
      if (u.origin === window.location.origin) url = `${SITE}${u.pathname}${u.search}${u.hash}`
    } catch { /* keep it as written */ }
    if (!url || url.startsWith('javascript:') || seen.has(url)) return
    seen.add(url)
    const own = cellText(a)
    const named = a.closest('[data-source-label]')?.getAttribute('data-source-label')
    out.push({ label: named ? `${named} (${own})` : own, url })
  }
  const marked = document.querySelectorAll<HTMLElement>('[data-page-sources]')
  if (marked.length) {
    marked.forEach(m => m.querySelectorAll<HTMLAnchorElement>('a[href]').forEach(add))
    return out
  }
  for (const h of Array.from(document.querySelectorAll('main h2, main h3, h2, h3'))) {
    if (!/^sources?\b/i.test(cellText(h))) continue
    const level = Number(h.tagName[1])
    for (let n = h.nextElementSibling; n; n = n.nextElementSibling) {
      if (/^H[1-6]$/.test(n.tagName) && Number(n.tagName[1]) <= level) break
      n.querySelectorAll<HTMLAnchorElement>('a[href]').forEach(add)
    }
  }
  return out
}

/** A table read off the page. The view is whichever switch near it is pressed, if any. */
export function specFromTable(t: HTMLTableElement): ExportSpec {
  const pressed = t.closest('figure')?.querySelector('[aria-pressed="true"], [aria-selected="true"]')
  const note = t.dataset.note ? [t.dataset.note] : []
  return {
    caption: tableCaption(t),
    views: [{ label: pressed ? (pressed.textContent ?? '').trim() : undefined, note, grid: gridFromTable(t) }],
  }
}

/* ------------------------------------------------------------------ the file */

const slug = (s: string, n = 48) => s.toLowerCase().normalize('NFKD').replace(/[^\w\s-]/g, '')
  .replace(/[\s_-]+/g, '-').replace(/^-|-$/g, '').slice(0, n).replace(/-$/, '')

function pageInfo() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const title = document.title.replace(/\s*[|·–—-]\s*Lunenburg Budget Project\s*$/i, '').trim() || document.title
  return {
    title, path,
    url: `${SITE}${path === '/' ? '/' : path}${window.location.search}`,
    page: slug(path.split('/').filter(Boolean).pop() ?? 'home') || 'home',
    host: SITE.replace(/^https?:\/\//, ''),
    date: new Date().toISOString().slice(0, 10),
  }
}

export function fileName(spec: ExportSpec, view?: string): string {
  const p = pageInfo()
  const t = slug(spec.caption, 40) || 'table'
  const v = view ? slug(view, 24) : ''
  return [p.page, t !== p.page ? t : '', v].filter(Boolean).join('-')
}

/** Rows that say what the table is, above the data. */
function contextRows(spec: ExportSpec, view: ExportView): Value[][] {
  const p = pageInfo()
  const rows: Value[][] = [['Table', spec.caption || '(untitled table)']]
  if (view.label) rows.push(['View', view.label])
  rows.push(['Page', p.title], ['Address', p.url], ['Downloaded', `${p.date} from ${p.host}`])
  for (const n of view.note ?? []) if (n.trim()) rows.push(['Note', n.trim()])
  return rows
}

const csvCell = (v: Value): string => {
  if (v == null) return ''
  if (typeof v === 'number') return String(v)
  // A text cell a spreadsheet would run as a formula is written as text.
  const s = /^[=+@]/.test(v) ? `'${v}` : v
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCSV(spec: ExportSpec, i: number, sources: Source[]): string {
  const view = spec.views[i]
  const typed = typeGrid(view.grid)
  const lines: Value[][] = [...contextRows(spec, view), [], typed.columns, ...typed.rows]
  if (sources.length) lines.push([], ['Sources'], ...sources.map(s => [s.label, s.url]))
  // A byte-order mark and CRLF: what Excel needs to open UTF-8 (a dash, a dagger) correctly.
  return '﻿' + lines.map(r => r.map(csvCell).join(',')).join('\r\n') + '\r\n'
}

function save(blob: Blob, name: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 4000)
}

const sheetName = (s: string, used: Set<string>) => {
  let base = s.replace(/[[\]:*?/\\]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 31) || 'Table'
  let name = base, n = 2
  while (used.has(name.toLowerCase())) { const sfx = ` (${n++})`; name = base.slice(0, 31 - sfx.length) + sfx }
  used.add(name.toLowerCase())
  return name
}

/** The workbook: a sheet per view, the context above each, and the sources on their own sheet.
 *  The writer (write-excel-file, MIT) is loaded only when somebody asks for a workbook, so it
 *  adds nothing to the page every reader downloads. */
export async function toXLSX(spec: ExportSpec, sources: Source[]): Promise<Blob> {
  const { default: write } = await import('write-excel-file/browser')
  const used = new Set<string>()
  const bold = { fontWeight: 'bold' as const }
  const sheets = spec.views.map((view, i) => {
    const typed = typeGrid(view.grid)
    const ctx = contextRows(spec, view).map(r => r.map((v, j) => (j === 0 ? { value: String(v), ...bold } : v)))
    const head = typed.columns.map(c => ({ value: c, ...bold, wrap: true }))
    const body = typed.rows.map(r => r.map((v, c) => (typeof v === 'number'
      ? { value: v, type: Number, format: typed.formats[c] } : v)))
    const widths = typed.columns.map((c, k) => ({
      width: Math.min(60, Math.max(10, c.length * 0.7, ...typed.rows.map(r => String(r[k] ?? '').length + 2))),
    }))
    return {
      sheet: sheetName(view.label || (spec.views.length > 1 ? `View ${i + 1}` : spec.caption || 'Table'), used),
      data: [...ctx, [], head, ...body] as never,
      columns: widths,
    }
  })
  if (sources.length) {
    sheets.push({
      sheet: sheetName('Sources', used),
      data: [[{ value: 'Source', ...bold }, { value: 'Address', ...bold }], ...sources.map(s => [s.label, s.url])] as never,
      columns: [{ width: 60 }, { width: 80 }],
    })
  }
  return write(sheets).toBlob()
}

export async function download(spec: ExportSpec, kind: 'csv' | 'xlsx'): Promise<void> {
  const sources = pageSources()
  const cur = Math.min(spec.current ?? 0, spec.views.length - 1)
  if (kind === 'csv') {
    const name = fileName(spec, spec.views.length > 1 ? spec.views[cur].label : undefined)
    save(new Blob([toCSV(spec, cur, sources)], { type: 'text/csv;charset=utf-8' }), `${name}.csv`)
  } else {
    save(await toXLSX(spec, sources), `${fileName(spec)}.xlsx`)
  }
}
