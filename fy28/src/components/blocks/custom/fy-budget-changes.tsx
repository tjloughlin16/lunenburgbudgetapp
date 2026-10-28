/** BUDGET CHANGES AFTER THE VOTE (fy-breakdown). TJ, 27 October 2026: "it needs to be more visible
 *  ... we could see the original budget, adjusted budget, diff with the flag for each row. or
 *  different table specifically for adjusted budget, showing top X expandable".
 *
 *  The page's year: every school line whose final budget is not what was voted, largest change
 *  first -- voted, transfers, carried in, final, the change -- the largest few shown and the rest
 *  behind a button. A line opens a popup of the transfers that changed it, each with the lines on
 *  the other side of the entry. Every figure is formatted by scripts/build_fy_breakdown.py
 *  (budget_changes_data), which checks each line's transfers sum to its change. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type Move = { date: string; memo: string; v: string; n: number; others: { line: string; v: string }[] }
type Row = { cat: string; line: string; acct: string; voted: string; transfers: string; carried: string; final: string
  n_voted: number; n_transfers: number; n_carried: number; n_final: number
  walk: string; adj: number; adj_t: string; adj_pct: string; flag: boolean; moves: Move[] }
type Year = { fy: string; rows: Row[]; n: number; n_flag: number }
type Data = { years: Year[]; show: number; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const FLAG = { color: 'var(--thread-3)', fontWeight: 600 }

/** SORTABLE (TJ, 28 October 2026). Words sort A to Z first, money largest first; the change sorts
 *  by size either way, as the table opens. "Show all" applies after the sort, so the first ten
 *  are the first ten of whatever order was picked. */
type Key = 'cat' | 'line' | 'voted' | 'transfers' | 'carried' | 'final' | 'change'
const VALUE: Record<Key, (r: Row) => string | number> = {
  cat: r => r.cat, line: r => r.line, voted: r => r.n_voted, transfers: r => r.n_transfers,
  carried: r => r.n_carried, final: r => r.n_final, change: r => Math.abs(r.adj) }
const WORDS: Key[] = ['cat', 'line']

function MovesView({ r, fy, t, onClose }: { r: Row; fy: string; t: Record<string, string>; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.line}
        className="w-full max-w-3xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 px-4 sm:px-6 pt-4 pb-3 border-b" style={{ background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' }}>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {r.cat}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{r.line}</h3>
              <p className="text-[11.5px]" style={muted}>{r.acct}</p>
            </div>
            <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)' }}>{t.close} ✕</button>
          </div>
          <p className="text-[13px] mt-2 tabular-nums" style={r.flag ? FLAG : secondary}>{r.flag ? '⚑ ' : ''}{r.walk}</p>
        </div>
        <div className="px-4 sm:px-6 py-4 space-y-4">
          {r.carried ? <p className="text-[13px]"><span style={secondary}>{t.carried_note}</span> <span className="font-semibold tabular-nums">{r.carried}</span></p> : null}
          {r.moves.length ? (
            <section>
              <p className="text-[12px] font-semibold uppercase tracking-wide" style={muted}>{t.moves}</p>
              <ul className="mt-1.5 space-y-3">
                {r.moves.map((m, i) => (
                  <li key={i} className="text-[13px]">
                    <div className="flex justify-between gap-3">
                      <span>{m.date} · <span style={secondary}>“{m.memo}”</span></span>
                      <span className="tabular-nums font-semibold whitespace-nowrap" style={{ color: m.n < 0 ? 'var(--thread-1)' : 'var(--thread-2)' }}>{m.v}</span>
                    </div>
                    {m.others.length ? (
                      <div className="mt-1 pl-3 border-l" style={{ borderColor: 'var(--grid)' }}>
                        <p className="text-[11.5px]" style={muted}>{t.other_side}</p>
                        <ul className="text-[12.5px]">
                          {m.others.map((o, k) => (
                            <li key={k} className="flex justify-between gap-3"><span style={secondary}>{o.line}</span>
                              <span className="tabular-nums whitespace-nowrap" style={secondary}>{o.v}</span></li>))}
                        </ul>
                      </div>) : null}
                  </li>))}
              </ul>
            </section>) : <p className="text-[13px]" style={muted}>{t.no_moves}</p>}
        </div>
      </div>
    </div>, document.body)
}

export default function FyBudgetChanges({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [all, setAll] = useState(false)
  const [view, setView] = useState<Row | null>(null)
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'change', dir: -1 })
  const sorted = useMemo(() => [...y.rows].sort((a, b) => {
    const x = VALUE[sort.key](a), z = VALUE[sort.key](b)
    return sort.dir * (typeof x === 'number' && typeof z === 'number' ? x - z : String(x).localeCompare(String(z)))
  }), [y, sort])
  const rows = all ? sorted : sorted.slice(0, d.show)
  const head = (key: Key, label: string) => (
    <th className={`px-2 py-1.5 font-semibold whitespace-nowrap cursor-pointer select-none ${WORDS.includes(key) ? 'text-left' : 'text-right'}`}
      aria-sort={sort.key === key ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}
      onClick={() => setSort(s => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : (WORDS.includes(key) ? 1 : -1) }))}>
      {label}{sort.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  const num = 'px-2 py-1.5 text-right whitespace-nowrap tabular-nums'
  return (
    <figure aria-label={alt}>
      <p className="text-[13.5px]"><span className="font-semibold tabular-nums">{y.n}</span> <span style={secondary}>{t.lines}</span>
        {y.n_flag ? <> · <span style={FLAG}>⚑ {y.n_flag} {t.flagged}</span></> : null}
        <span className="ml-3 text-[12.5px]" style={muted}>{t.open} · {t.sort}</span></p>
      <WideScroll cue={t.lines}>
        <table className="w-full min-w-[900px] text-[13px] border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              {head('cat', t.cat)}{head('line', t.line)}{head('voted', t.voted)}{head('transfers', t.transfers)}
              {head('carried', t.carried)}{head('final', t.final)}{head('change', t.change)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b align-top cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                onClick={() => setView(r)} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setView(r) }}>
                <td className="px-2 py-1.5 min-w-[9rem]" style={secondary}>{r.cat}</td>
                <td className="px-2 py-1.5 min-w-[16rem]"><span className="underline decoration-dotted underline-offset-2">{r.line}</span>
                  <span className="block text-[11px]" style={muted}>{r.acct}</span></td>
                <td className={num} style={secondary}>{r.voted}</td>
                <td className={num} style={secondary}>{r.transfers}</td>
                <td className={num} style={secondary}>{r.carried}</td>
                <td className={num}>{r.final}</td>
                <td className={num} style={r.flag ? FLAG : undefined}>{r.flag ? '⚑ ' : ''}{r.adj_t}
                  {r.adj_pct ? <span className="block text-[11px] font-normal">{r.adj_pct}</span> : null}</td>
              </tr>))}
          </tbody>
        </table>
      </WideScroll>
      {y.rows.length > d.show ? (
        <button type="button" className="mt-2 text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
          onClick={() => setAll(a => !a)}>{all ? t.show_fewer : `${t.show_all} ${y.n}`}</button>) : null}
      <p className="text-[12px] mt-2" style={muted}>{t.flag_means}</p>
      {view ? <MovesView r={view} fy={y.fy} t={t} onClose={() => setView(null)} /> : null}
    </figure>)
}
