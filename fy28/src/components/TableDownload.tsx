import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { download, specFromTable, type ExportSpec } from '../lib/tableExport'

/** THE DOWNLOAD CONTROL, one for every table on the site (lib/tableExport.ts says why and how).
 *
 *  Small and quiet on purpose: a line of muted text at the table's top-right, "Download CSV ·
 *  Excel", not a button that competes with the table. Two real <button>s, so it is reachable by
 *  keyboard and says what it does to a screen reader. `no-print`: a download link on paper is
 *  ink nobody can press. */
export function TableDownload({ spec, className }: { spec: () => ExportSpec; className?: string }) {
  const [busy, setBusy] = useState<'' | 'csv' | 'xlsx'>('')
  const go = async (kind: 'csv' | 'xlsx', e: React.MouseEvent) => {
    e.stopPropagation()
    setBusy(kind)
    try { await download(spec(), kind) } finally { setBusy('') }
  }
  const btn = 'underline decoration-dotted underline-offset-2 hover:decoration-solid px-1 py-1 min-h-[24px] cursor-pointer'
  return (
    <div className={`tbl-dl no-print flex justify-end items-center gap-0.5 text-[12px] leading-none ${className ?? ''}`}
      style={{ color: 'var(--text-muted)' }} data-table-download="">
      <span aria-hidden>Download</span>
      <button type="button" className={btn} onClick={e => go('csv', e)} aria-label="Download this table as CSV"
        disabled={!!busy}>{busy === 'csv' ? 'CSV…' : 'CSV'}</button>
      <span aria-hidden>·</span>
      <button type="button" className={btn} onClick={e => go('xlsx', e)} aria-label="Download this table as an Excel workbook"
        disabled={!!busy}>{busy === 'xlsx' ? 'Excel…' : 'Excel'}</button>
    </div>
  )
}

/* ------------------------------------------------------------------ every other table
 * THE ENHANCER. Mounted once in App.tsx. It watches the page and gives every data <table> the
 * same control, read off the table itself (gridFromTable), so a markdown analysis, a bespoke
 * page and a ledger all get it without each being edited -- and a table added next month gets
 * it too.
 *
 * Left alone:
 *  - a table that brings its own control (`data-download="own"`: FigureTable, whose payload
 *    holds exact values and every view);
 *  - a table nobody sees as a table: inside `aria-hidden` (the presence matrix's dots, which
 *    exports from its payload instead) or `.sr-only` (a chart's figures for a screen reader);
 *  - anything marked `data-no-download`, and a table with fewer than one data row.
 *
 * HOW IT SITS BESIDE REACT. The control's host is a plain <div> inserted just before the table
 * (or before the table's own scroll box), and React renders into it through a portal. React
 * never removes or reorders a node it did not create, so the host survives re-renders; when the
 * table goes, its host is taken away here. Not during prerender (navigator.webdriver): the
 * static twin of a page is for readers who cannot run the button anyway. */
type Slot = { table: HTMLTableElement; host: HTMLElement }

const wanted = (t: HTMLTableElement) =>
  t.isConnected
  && t.dataset.download !== 'own'
  && !t.closest('[aria-hidden="true"], .sr-only, [data-no-download], .tbl-dl')
  && t.querySelectorAll('tbody tr, tr').length > 1

/** Where the control goes: before the table, or before the box that scrolls it sideways. */
function anchorFor(t: HTMLTableElement): Element {
  const p = t.parentElement
  if (p && p.children.length === 1 && p !== document.body) {
    const ox = getComputedStyle(p).overflowX
    if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return p
  }
  return t
}

export function TableDownloads() {
  const [slots, setSlots] = useState<Slot[]>([])
  useEffect(() => {
    const w = window as unknown as { __TABLE_DOWNLOADS__?: boolean }
    if (navigator.webdriver && !w.__TABLE_DOWNLOADS__) return
    const hosts = new Map<HTMLTableElement, HTMLElement>()
    let raf = 0
    const scan = () => {
      raf = 0
      let changed = false
      for (const [t, h] of hosts) {
        if (!wanted(t)) { h.remove(); hosts.delete(t); changed = true }
        else if (!h.isConnected || h.nextElementSibling !== anchorFor(t)) {
          const a = anchorFor(t)
          a.parentNode?.insertBefore(h, a)
        }
      }
      for (const t of Array.from(document.querySelectorAll<HTMLTableElement>('#root table'))) {
        if (hosts.has(t) || !wanted(t)) continue
        const a = anchorFor(t)
        const h = document.createElement('div')
        h.className = 'tbl-dl-host no-print'
        a.parentNode?.insertBefore(h, a)
        hosts.set(t, h)
        changed = true
      }
      if (changed) setSlots(Array.from(hosts, ([table, host]) => ({ table, host })))
    }
    const mo = new MutationObserver(muts => {
      // Our own hosts changing is not news.
      if (muts.every(m => (m.target as Element).closest?.('.tbl-dl-host'))) return
      if (!raf) raf = requestAnimationFrame(scan)
    })
    mo.observe(document.getElementById('root') ?? document.body, { childList: true, subtree: true })
    scan()
    return () => {
      mo.disconnect()
      if (raf) cancelAnimationFrame(raf)
      for (const h of hosts.values()) h.remove()
    }
  }, [])
  return <>{slots.map(s => createPortal(
    <TableDownload className="mb-1" spec={() => specFromTable(s.table)} />, s.host, keyOf(s.table)))}</>
}

const keys = new WeakMap<HTMLTableElement, string>()
let nextKey = 0
const keyOf = (t: HTMLTableElement) => {
  let k = keys.get(t)
  if (!k) { k = `t${nextKey++}`; keys.set(t, k) }
  return k
}

export default TableDownload
