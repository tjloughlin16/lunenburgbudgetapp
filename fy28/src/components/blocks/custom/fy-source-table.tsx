/** WHAT OTHER FUNDS PAID FOR (fy-breakdown). TJ, 27 October 2026: "what the non-general fund paid
 *  for, in a table. so that we know per source what was paid for ... maybe we need a similar
 *  table for the other sources?"
 *
 *  The big table reads by school line; this one reads by FUND, for the page's year: every fund
 *  other than the school budget that spent on the schools, its spending in the six ways it can
 *  land, summing to everything it spent. A row opens a popup -- where its money went, what it
 *  bought (by its own account and by payee), every posting -- from
 *  /data/fy-breakdown/funds-<year>.json, fetched when a fund is opened.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { HeadTip, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type K = 'payee' | 'function' | 'later' | 'back' | 'capital' | 'none' | 'total'
type Row = { key: string; name: string; printed: string; program: string; cat: string; group: string; n: Record<K, number>; t: Record<K, string> }
type Year = { fy: string; rows: Row[]; total: string }
type Col = { id: K; label: string; means: string }
type T = Record<'source' | 'category' | 'read' | 'tab_where' | 'tab_what' | 'tab_rows' | 'by_payee' | 'by_account' | 'went'
  | 'close' | 'loading' | 'failed' | 'none' | 'sum' | 'all_rows' | 'all_cats' | 'scroll' | 'filter', string>
type Data = { years: Year[]; columns: Col[]; groups: { id: string; label: string }[]; text: T }
type Pair = [string, string, number]
type Posting = [string, string, string, string, string, string, string, string, number]
type Fund = { w: [string, string, string, number][]; a: Pair[]; p: Pair[]; r: Posting[] }
type File = { fy: string; funds: Record<string, Fund> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const PAYER: Record<string, string> = { idea: 'var(--thread-2)', grants: 'var(--thread-5)', cb: 'var(--thread-4)',
  fees: 'var(--thread-3)', other: 'var(--thread-6, var(--text-secondary))' }
const FILES = new Map<string, Promise<File>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/funds-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

/** Amounts as bars against the largest, so a list reads at a glance. */
function Bars({ title, items }: { title: string; items: { label: string; sub?: string; text: string; v: number }[] }) {
  const max = Math.max(1, ...items.map(i => Math.abs(i.v)))
  return (
    <div className="text-[13px]">
      <p className="font-semibold mb-1">{title}</p>
      <ul className="space-y-1.5">
        {items.map((i, k) => (
          <li key={k}>
            <div className="flex justify-between gap-3"><span>{i.sub ? <span style={muted}>{i.sub} </span> : null}{i.label}</span>
              <span className="tabular-nums font-semibold whitespace-nowrap">{i.text}</span></div>
            <span className="block h-1.5 rounded-sm mt-0.5" style={{ width: `${(Math.abs(i.v) / max) * 100}%`,
              background: i.v < 0 ? 'var(--text-muted)' : 'var(--thread-2)' }} />
          </li>))}
      </ul>
    </div>)
}

function FundView({ r, fy, t, onClose }: { r: Row; fy: string; t: T; onClose: () => void }) {
  const [tab, setTab] = useState<'where' | 'what' | 'rows'>('where')
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState(false)
  const [q, setQ] = useState('')
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => { let live = true; load(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) }); return () => { live = false } }, [fy])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  const F = file?.funds[r.key]
  const rows = useMemo(() => {
    if (!F) return []
    const s = q.trim().toLowerCase()
    return s ? F.r.filter(x => [x[2], x[3], x[4], x[5], x[6]].some(v => v.toLowerCase().includes(s))) : F.r
  }, [F, q])
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.name}
        className="w-full max-w-6xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 px-4 sm:px-6 pt-4 pb-3 border-b" style={{ background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' }}>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {r.cat}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{r.name}</h3>
              <p className="text-[11.5px]" style={muted}>{r.printed}</p>
              <p className="text-[12.5px] mt-0.5" style={muted}>{r.program} · {r.t.total}</p>
            </div>
            <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)' }}>{t.close} ✕</button>
          </div>
          <div className="flex gap-1.5 mt-3">
            <Chip on={tab === 'where'} onClick={() => setTab('where')}>{t.tab_where}</Chip>
            <Chip on={tab === 'what'} onClick={() => setTab('what')}>{t.tab_what}</Chip>
            <Chip on={tab === 'rows'} onClick={() => setTab('rows')}>{t.tab_rows}</Chip>
          </div>
        </div>
        <div className="px-4 sm:px-6 py-4">
          {err ? <p className="text-[13px]" style={muted}>{t.failed}</p> : !F ? <p className="text-[13px]" style={muted}>{t.loading}</p>
            : tab === 'where' ? (
              <div className="max-w-3xl"><Bars title={t.tab_where} items={F.w.map(([k, w, tx, v]) => ({ sub: k, label: w, text: tx, v }))} /></div>
            ) : tab === 'what' ? (
              <div className="grid gap-6 md:grid-cols-2">
                <Bars title={t.by_account} items={F.a.map(([l, tx, v]) => ({ label: l, text: tx, v }))} />
                <Bars title={t.by_payee} items={F.p.map(([l, tx, v]) => ({ label: l, text: tx, v }))} />
              </div>
            ) : (
              <div>
                <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter}
                  className="mb-2 w-full max-w-sm px-2 py-1 rounded border text-[13px]"
                  style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
                <p className="text-[12px] mb-1" style={muted}>{rows.length} · {t.all_rows}</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-[12.5px] tabular-nums border-collapse">
                    <tbody>
                      {rows.map((x, i) => (
                        <tr key={i} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                          <td className="px-1.5 py-1 whitespace-nowrap" style={secondary}>{x[1]}</td>
                          <td className="px-1.5 py-1 whitespace-nowrap" style={muted}>{x[2]}</td>
                          <td className="px-1.5 py-1">{x[3] || <span style={muted}>—</span>}<span className="block text-[11.5px]" style={muted}>{x[4]}</span></td>
                          <td className="px-1.5 py-1" style={secondary}>{x[5]}<span className="block text-[11.5px]" style={muted}>{t.went}: {x[6]}</span></td>
                          <td className="px-1.5 py-1 text-right whitespace-nowrap font-semibold">{x[7]}</td>
                        </tr>))}
                    </tbody>
                  </table>
                </div>
              </div>)}
        </div>
      </div>
    </div>, document.body)
}

export default function FySourceTable({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [grp, setGrp] = useState('')
  const [sort, setSort] = useState<{ k: K | 'cat'; dir: 1 | -1 }>({ k: 'total', dir: -1 })
  const [open, setOpen] = useState<string | null>(null)
  const close = useCallback(() => setOpen(null), [])
  const rows = useMemo(() => y.rows.filter(r => !grp || r.group === grp).sort((a, b) =>
    sort.k === 'cat' ? sort.dir * b.cat.localeCompare(a.cat) || b.n.total - a.n.total
      : sort.dir * (a.n[sort.k] - b.n[sort.k]) || a.name.localeCompare(b.name)), [y, grp, sort])
  const openRow = open ? y.rows.find(r => r.key === open) ?? null : null
  const head = (c: Col) => (
    <th key={c.id} className={`px-2 py-1.5 text-right align-bottom cursor-pointer select-none ${c.id === 'total' ? 'border-l' : ''}`}
      style={{ borderColor: 'var(--grid)' }} onClick={() => setSort(s => ({ k: c.id, dir: s.k === c.id ? (-s.dir as 1 | -1) : -1 }))}
      aria-sort={sort.k === c.id ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
      <span className="block text-[15px] leading-none mb-1" style={muted}>{c.id === 'total' ? '=' : c.id === 'payee' ? ' ' : '+'}</span>
      <HeadTip label={c.label} means={c.means}><span className="font-semibold">{c.label}{sort.k === c.id ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></HeadTip></th>)
  return (
    <figure aria-label={alt}>
      <p className="text-[14px] leading-snug max-w-3xl" style={secondary}>{t.read}</p>
      <div className="flex flex-wrap gap-1.5 items-center mt-3">
        <Chip on={!grp} onClick={() => setGrp('')}>{t.all_cats}</Chip>
        {d.groups.filter(g => y.rows.some(r => r.group === g.id)).map(g => (
          <Chip key={g.id} on={grp === g.id} onClick={() => setGrp(g.id)}>
            <span className="inline-block w-2 h-2 rounded-[1px] mr-1 align-middle" style={{ background: PAYER[g.id] }} />{g.label}</Chip>))}
      </div>
      <WideScroll cue={t.scroll}>
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold">{t.source}</th>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold cursor-pointer select-none"
                onClick={() => setSort(s => ({ k: 'cat', dir: s.k === 'cat' ? (-s.dir as 1 | -1) : -1 }))}>
                {t.category}{sort.k === 'cat' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>
              {d.columns.map(head)}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                onClick={() => setOpen(r.key)} aria-haspopup="dialog">
                <td className="px-2 py-1.5 text-left min-w-[14rem]"><span className="mr-1" style={muted}>↗</span>{r.name}
                  <span className="block pl-4 text-[11px]" style={muted}>{r.printed}</span></td>
                <td className="px-2 py-1.5 text-left min-w-[9rem]" style={secondary}>
                  <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[r.group] }} />{r.cat}</td>
                {d.columns.map(c => (
                  <td key={c.id} className={`px-2 py-1.5 text-right whitespace-nowrap ${c.id === 'total' ? 'border-l font-semibold' : ''}`}
                    style={{ borderColor: 'var(--grid)' }}>
                    {Math.abs(r.n[c.id]) < 0.5 ? <span style={muted}>·</span> : r.t[c.id]}</td>))}
              </tr>))}
            {!grp ? (
              <tr>
                <td className="px-2 py-1.5 font-semibold" colSpan={2 + d.columns.length - 1}>{t.sum}</td>
                <td className="px-2 py-1.5 text-right font-semibold border-l" style={{ borderColor: 'var(--grid)' }}>{y.total}</td>
              </tr>) : null}
          </tbody>
        </table>
      </WideScroll>
      {openRow ? <FundView r={openRow} fy={y.fy} t={t} onClose={close} /> : null}
    </figure>)
}
