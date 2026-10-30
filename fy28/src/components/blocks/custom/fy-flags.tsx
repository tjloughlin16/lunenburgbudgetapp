/** LINES FLAGGED AGAINST THEIR VOTE (fy-breakdown). Follows the page's year picker (fy-year.ts).
 *
 *  Three panels for the picked year -- underfunded, overbudgeted, restarted high -- each with its
 *  rule and threshold (ours) and its lines, largest first; a line opens on its transfers and
 *  links to its page. The same flags, every line and every year, are the grid on
 *  /school-all-funds/budget-against-actual (TJ, 29 October 2026: one question per page -- the
 *  year's story here, the pattern across years there). Every string and figure is the payload's
 *  (scripts/line_flags.py, year_block()). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'
import { itemHrefs, useItemIndex, withYear } from './fy-items'

export type FlagKey = 'under' | 'over' | 'restart'
type Move = { date: string; memo: string; v: string; others: string[] }
type FRow = { name: string; account: string; cat: string; voted: string; spent: string; f: FlagKey[]
  under?: { gap: string; covered: string; uncovered: string; n: number; recharged: string }
  over?: { unspent: string; out: string; left: string; n: number; recharged: string }
  restart?: { over: string; prior_spent: string; prior_budget: string; cut: boolean; above_budget: boolean; thin: boolean; n: number }
  moves?: Move[] }
type Year = { fy: string; rows: FRow[]; counts: Record<FlagKey, string>; lines: string; new: string | null; no_restart: string | null }
type Flag = { name: string; rule: string; means: string }
type Data = { years: Year[]; flags: Record<FlagKey, Flag> & { ours: string; why: string }; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }
const link = { color: 'var(--link, var(--thread-2))' }
const KEYS: FlagKey[] = ['under', 'over', 'restart']
const FIRST = 6
export const FLAG_TONE: Record<FlagKey, string> = { under: 'var(--thread-1)', over: 'var(--thread-2)', restart: 'var(--thread-4)' }

function Figs({ items }: { items: [string, string][] }) {
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-[12.5px] tabular-nums">
      {items.filter(([, v]) => v).map(([k, v]) => <span key={k}><span style={muted}>{k} </span><span className="font-semibold">{v}</span></span>)}
    </span>)
}

function FlagItem({ r, k, t, fy, href }: { r: FRow; k: FlagKey; t: Data['text']; fy: string; href?: string }) {
  const [open, setOpen] = useState(false)
  const figs: [string, string][] = k === 'under' && r.under
    ? [[t.gap, r.under.gap], [t.covered, r.under.covered], [t.uncovered, r.under.uncovered], [t.recharged, r.under.recharged]]
    : k === 'over' && r.over
      ? [[t.unspent, r.over.unspent], [t.moved_out, r.over.out], [t.left_end, r.over.left], [t.recharged, r.over.recharged]]
      : r.restart ? [[t.over_by, r.restart.over], [t.prior_spent, r.restart.prior_spent], [t.prior_budget, r.restart.prior_budget]] : []
  const notes = k === 'restart' && r.restart ? [
    r.restart.cut ? t.cut : '', r.restart.above_budget ? t.above : t.below, r.restart.thin ? t.thin : ''].filter(Boolean) : []
  return (
    <li className="py-2 border-b" style={{ borderColor: 'var(--grid)' }}>
      <div className="flex flex-wrap justify-between gap-x-3">
        <span className="text-[13.5px]">
          {href ? <a href={withYear(href, fy)} className="underline" style={link}>{r.name}</a> : r.name}
          <span className="block text-[11.5px]" style={muted}>{r.cat} · {t.voted} {r.voted} · {t.spent} {r.spent}</span>
        </span>
        {r.moves?.length ? (
          <button type="button" className="text-[12px] underline self-start" style={link} aria-expanded={open}
            onClick={() => setOpen(o => !o)}>{t.transfers} ({r.moves.length})</button>) : null}
      </div>
      <div className="mt-1"><Figs items={figs} /></div>
      {notes.map(n => <p key={n} className="text-[12px] mt-0.5" style={muted}>{n}</p>)}
      {open && r.moves ? (
        <ul className="mt-1.5 space-y-1 text-[12px]">
          {r.moves.map((m, i) => (
            <li key={i} className="pl-2 border-l" style={{ borderColor: 'var(--grid)' }}>
              <span className="tabular-nums font-semibold">{m.v}</span> · {m.date} · <span style={muted}>{m.memo}</span>
              {m.others.length ? <span className="block" style={muted}>{t.other_side} {m.others.join(', ')}</span> : null}
            </li>))}
        </ul>) : null}
    </li>)
}

function FlagPanel({ k, y, d, href }: { k: FlagKey; y: Year; d: Data; href: (a: string) => string | undefined }) {
  const [all, setAll] = useState(false)
  const t = d.text, f = d.flags[k]
  const rows = y.rows.filter(r => r[k]).sort((a, b) => b[k]!.n - a[k]!.n)
  const blocked = k === 'restart' ? y.no_restart : null
  return (
    <section className="rounded border p-3" style={{ borderColor: 'var(--grid)', borderTop: `3px solid ${FLAG_TONE[k]}` }}>
      <p className="text-[15px] font-semibold">{f.name}
        {!blocked ? <span className="ml-2 tabular-nums">{y.counts[k]}</span> : null}
        {!blocked ? <span className="ml-1 text-[12px] font-normal" style={muted}>{t.of} {y.lines} {t.lines_n} {t.flagged}</span> : null}</p>
      <p className="text-[12.5px] mt-1">{f.rule}</p>
      <p className="text-[12.5px] mt-1" style={muted}>{f.means}</p>
      {blocked ? <p className="text-[13px] mt-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>{blocked}</p> : (
        <>
          <ul className="mt-2">{(all ? rows : rows.slice(0, FIRST)).map(r => (
            <FlagItem key={r.account} r={r} k={k} t={t} fy={y.fy} href={href(r.account)} />))}</ul>
          {rows.length > FIRST ? (
            <button type="button" className="mt-2 text-[12.5px] underline" style={link} onClick={() => setAll(a => !a)}>
              {all ? t.show_fewer : `${t.show_all} (${rows.length})`}</button>) : null}
          {k === 'restart' && y.new ? <p className="text-[12px] mt-2" style={muted}>{y.new}</p> : null}
        </>)}
    </section>)
}

export default function FyFlags({ data, alt }: CustomProps) {
  const d = data as Data
  const all = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(all)
  const y = d.years.find(v => v.fy === fy) ?? d.years[d.years.length - 1]
  const hrefs = itemHrefs(useItemIndex())
  return (
    <figure aria-label={alt}>
      <div className="grid gap-3 md:grid-cols-3">
        {KEYS.map(k => <FlagPanel key={`${y.fy}-${k}`} k={k} y={y} d={d} href={hrefs.line} />)}
      </div>
      <p className="text-[12px] mt-2" style={muted}>{d.flags.ours} {d.flags.why}</p>
      <p className="text-[12.5px] mt-1"><a href={d.text.across_href} className="underline" style={link}>{d.text.across}</a></p>
    </figure>)
}
