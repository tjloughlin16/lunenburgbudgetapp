/** SCHOOL LINES OTHER FUNDS PAID (fy-breakdown). TJ, 27 October 2026: "which of the school budget
 *  lines were paid by non general fund money ... athletics lines XYZ - paid by FUND X - an amount",
 *  then "group lines together ... that are the same school line, aggregates, but listing the funds
 *  paying it, with details available by clicking".
 *
 *  The sister of "What other funds paid for": the same placements, read by school line. One row
 *  per line for the page's year -- what other funds paid toward it in all, the line's budget and
 *  the share of its cost, and the funds as chips; a click opens a popup of each fund's amount and
 *  how we know (TJ: "put the row click into a popup. its too awkward to expand a table row").
 *  Sorted by what other funds paid, largest first.
 *  Every figure is formatted by scripts/build_fy_breakdown.py (line_funds_data), which ties the
 *  lines to the table of funds. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { HeadTip, PAYER, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type Fund = { fund: string; printed: string; group: string; how: string; n: number; t: string; share: string }
type Line = { cat: string; line: string; acct: string; n: number; t: string; budget: string; share: string
  groups: string[]; funds: Fund[] }
type Year = { fy: string; lines: Line[]; total: string; n_rows: number }
type Data = { years: Year[]; how: { id: string; label: string; means: string }[]
  groups: { id: string; label: string }[]; text: Record<string, string> }
type Key = 'cat' | 'line' | 'n' | 'funds'

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="px-2.5 py-1 rounded-full text-[12.5px]"
      style={{ border: '1px solid var(--grid)', background: on ? 'var(--text-primary)' : 'transparent',
        color: on ? 'var(--surface-1, #fff)' : 'var(--text-secondary)' }}>{children}</button>)
}

function LineView({ l, fy, t, kind, how, onClose }: { l: Line; fy: string; t: Record<string, string>
  kind: Record<string, string>; how: Record<string, { label: string; means: string }>; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  const max = Math.max(...l.funds.map(f => Math.abs(f.n)), 1)
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={l.line}
        className="w-full max-w-3xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 px-4 sm:px-6 pt-4 pb-3 border-b" style={{ background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' }}>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {l.cat}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{l.line}</h3>
              {l.acct ? <p className="text-[11.5px]" style={muted}>{l.acct}</p> : null}
            </div>
            <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)' }}>{t.close} ✕</button>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-2 text-[13px]">
            <span><span className="font-semibold tabular-nums">{l.t}</span> <span style={secondary}>{t.paid.toLowerCase()}</span></span>
            {l.budget ? <span><span className="font-semibold tabular-nums">{l.budget}</span> <span style={secondary}>{t.budget.toLowerCase()}</span></span> : null}
            {l.share ? <span><span className="font-semibold tabular-nums">{l.share}</span> <span style={secondary}>{t.share.toLowerCase()}</span></span> : null}
          </div>
        </div>
        <ul className="px-4 sm:px-6 py-4 space-y-3">
          {l.funds.map((f, i) => (
            <li key={i}>
              <div className="flex justify-between gap-3 text-[13.5px]">
                <span className="min-w-0"><span className="inline-block w-2.5 h-2.5 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[f.group] }} />
                  <span className="font-semibold">{f.fund}</span> <span className="text-[12px]" style={muted}>{kind[f.group]}</span>
                  <span className="block pl-4 text-[11px]" style={muted}>{f.printed}</span></span>
                <span className="tabular-nums font-semibold whitespace-nowrap">{f.t}{f.share ? <span className="font-normal text-[12px] ml-1.5" style={muted}>{f.share}</span> : null}</span>
              </div>
              <div className="h-2 mt-1 rounded-sm" style={{ width: `${(Math.abs(f.n) / max) * 100}%`, background: PAYER[f.group], opacity: f.n < 0 ? 0.4 : 1 }} />
              <p className="text-[12px] mt-1 leading-snug" style={secondary}><span className="font-semibold">{how[f.how].label}.</span> {how[f.how].means}</p>
            </li>))}
        </ul>
      </div>
    </div>, document.body)
}

export default function FyLineFunds({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const kind = Object.fromEntries(d.groups.map(g => [g.id, g.label]))
  const how = Object.fromEntries(d.how.map(h => [h.id, h]))
  const [grp, setGrp] = useState('')
  const [q, setQ] = useState('')
  const [view, setView] = useState<Line | null>(null)
  const [sort, setSort] = useState<{ k: Key; dir: 1 | -1 }>({ k: 'n', dir: -1 })
  const id = (l: Line) => `${l.acct}|${l.line}`
  // a kind of fund picked shows the lines it paid toward, and only its funds under them
  const lines = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const out = y.lines
      .filter(l => !grp || l.groups.includes(grp))
      .filter(l => !ql || `${l.line} ${l.cat} ${l.acct} ${l.funds.map(f => `${f.fund} ${f.printed}`).join(' ')}`.toLowerCase().includes(ql))
    return out.sort((a, b) => sort.k === 'n' ? sort.dir * (a.n - b.n)
      : sort.k === 'funds' ? sort.dir * (a.funds.length - b.funds.length) || b.n - a.n
      : sort.dir * a[sort.k].localeCompare(b[sort.k]) || b.n - a.n)
  }, [y, grp, q, sort])
  const head = (k: Key, label: string, right = false) => (
    <th className={`px-2 py-1.5 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => setSort(s => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : (k === 'n' || k === 'funds' ? -1 : 1) }))}>
      {label}{sort.k === k ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5">
        <Chip on={!grp} onClick={() => setGrp('')}>{t.all_kinds}</Chip>
        {d.groups.filter(g => y.lines.some(l => l.groups.includes(g.id))).map(g => (
          <Chip key={g.id} on={grp === g.id} onClick={() => setGrp(grp === g.id ? '' : g.id)}>
            <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[g.id] }} />{g.label}</Chip>))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
          className="w-full max-w-md px-2.5 py-1.5 rounded text-[13px]"
          style={{ border: '1px solid var(--grid)', background: 'transparent' }} />
        <span className="text-[12.5px]" style={muted}>{t.open}</span>
      </div>
      <WideScroll cue={t.scroll}>
        <table className="w-full min-w-[960px] text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              {head('cat', t.cat)}{head('line', t.line)}{head('funds', t.fund)}{head('n', t.paid, true)}
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.budget} means={t.budget_means}>{t.budget}</HeadTip></th>
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.share} means={t.share_means}>{t.share}</HeadTip></th>
            </tr>
          </thead>
          <tbody>
            {lines.map(l => {
              const funds = grp ? l.funds.filter(f => f.group === grp) : l.funds
              return (
                <tr key={id(l)} className="border-b align-top cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setView(l)} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setView(l) }}>
                  <td className="px-2 py-1.5" style={secondary}>{l.cat}</td>
                  <td className="px-2 py-1.5"><span className="underline decoration-dotted underline-offset-2">{l.line}</span>
                    {l.acct ? <span className="block text-[11px]" style={muted}>{l.acct}</span> : null}</td>
                  <td className="px-2 py-1.5">
                    <span className="inline-flex flex-wrap gap-1 items-center">
                      {l.groups.map(g => <span key={g} title={kind[g]} className="inline-block w-2 h-2 rounded-[1px]" style={{ background: PAYER[g] }} />)}
                      <span style={secondary}>{funds.length} {funds.length === 1 ? t.fund_one : t.funds}</span></span></td>
                  <td className="px-2 py-1.5 text-right whitespace-nowrap font-semibold">{l.t}</td>
                  <td className="px-2 py-1.5 text-right whitespace-nowrap" style={secondary}>{l.budget}</td>
                  <td className="px-2 py-1.5 text-right whitespace-nowrap" style={secondary}>{l.share}</td>
                </tr>)
            })}
          </tbody>
          <tfoot>
            <tr>
              <td className="px-2 py-1.5 font-semibold" colSpan={3}>{t.sum} · {lines.length} {t.lines}</td>
              <td className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">{!grp && !q.trim() ? y.total : ''}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </WideScroll>
      {view ? <LineView l={view} fy={y.fy} t={t} kind={kind} how={how} onClose={() => setView(null)} /> : null}
    </figure>)
}
