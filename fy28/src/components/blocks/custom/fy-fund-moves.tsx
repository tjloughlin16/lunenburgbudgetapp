/** COST MOVED BETWEEN FUNDS (fy-breakdown). TJ, 28 October 2026: "we also need to show that grant
 *  money is moved across years too.... FY25 moving to FY26 grants".
 *
 *  The page's year: every pair of funds a journal entry re-booked cost between, drawn as a flow
 *  from the fund the cost came off to the fund it went onto -- one grant's awards first, so a move
 *  from one year's award to the next reads as one row -- with the net and how many entries. A row
 *  opens its entries: date, memo, journal number, from, to, amount, a reversal marked on both.
 *  Every figure is formatted by scripts/build_fy_breakdown.py (moves_data) from the model's
 *  `fund_moves_between`; the pairing is the books' (fy_breakdown.pair). `MoveGroups` is shared
 *  with a fund's own page (FyItem.tsx), which shows the groups that touch its awards. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

export type MoveRow = { d: string; iso: string; memo: string; j: string; rev: string; school: boolean; a: string; b: string; t: string; n: number }
export type MoveGroup = { cls: string; prog: string; a: string; b: string; dir: 'later' | 'earlier' | null; t: string; n: number
  cancels: boolean; count: number; gross: string; rows: MoveRow[]; funds: string[] }
type Year = { fy: string; groups: MoveGroup[]; n: number; t: string; t_award: string; n_award: number; t_undone: string }
type Data = { years: Year[]; classes: { id: string; label: string }[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const AWARD = 'var(--thread-5)'

function Box({ label }: { label: string }) {
  const [name, num] = label.split(' · ')
  return (
    <div className="rounded border px-2.5 py-1.5 min-w-0 flex-1" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1, var(--bg))' }}>
      <span className="block text-[13px] leading-snug">{name}</span>
      {num ? <span className="block text-[11px]" style={muted}>{num}</span> : null}
    </div>)
}

function Flow({ g, t }: { g: MoveGroup; t: Record<string, string> }) {
  const c = g.cls === 'award' ? AWARD : 'var(--text-secondary)'
  return (
    <details className="rounded border" style={{ borderColor: 'var(--grid)' }}>
      <summary className="cursor-pointer list-none px-2.5 py-2">
        <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
          <Box label={g.a} />
          <div className="flex sm:flex-col items-center gap-1 sm:w-40 shrink-0 text-center" aria-hidden={false}>
            <span className="tabular-nums font-semibold text-[14px]" style={{ color: g.cancels ? 'var(--text-muted)' : c }}>
              {g.cancels ? t.cancels : g.t}</span>
            <svg viewBox="0 0 100 10" className="hidden sm:block w-full h-2.5" aria-hidden="true">
              <line x1="2" y1="5" x2="90" y2="5" stroke={c} strokeWidth="2" strokeDasharray={g.cancels ? '4 3' : undefined} />
              <path d="M88,0 L98,5 L88,10 z" fill={c} /></svg>
            <span className="sm:hidden" style={{ color: c }}>↓</span>
            <span className="text-[11.5px]" style={muted}>{g.count} {g.count === 1 ? t.entry : t.entries}
              {g.dir ? ` · ${t[g.dir]}` : ''}</span>
          </div>
          <Box label={g.b} />
        </div>
      </summary>
      <div className="px-2.5 pb-2.5">
        {g.cls === 'unpaired' ? <p className="text-[12.5px] mb-1.5" style={secondary}>{t.unpaired}</p> : null}
        <ul className="space-y-2 text-[13px]">
          {g.rows.map((r, i) => (
            <li key={i} className="border-t pt-1.5" style={{ borderColor: 'var(--grid)' }}>
              <div className="flex justify-between gap-3">
                <span>{r.d} · <span style={secondary}>“{r.memo}”</span></span>
                <span className="tabular-nums font-semibold whitespace-nowrap">{r.t}</span>
              </div>
              <p className="text-[12px]" style={muted}>{t.c_journal} {r.j} · {r.a.split(' · ')[0]} → {r.b.split(' · ')[0]}</p>
              {r.rev ? <p className="text-[12px] font-semibold" style={{ color: 'var(--thread-3)' }}>⇄ {r.rev}</p> : null}
              {r.school ? <p className="text-[12px]" style={muted}>{t.school}</p> : null}
            </li>))}
        </ul>
      </div>
    </details>)
}

/** The groups, under their class headings, in the order the generator sorted them. */
export function MoveGroups({ groups, classes, text }: { groups: MoveGroup[]; classes: { id: string; label: string }[]; text: Record<string, string> }) {
  if (!groups.length) return <p className="text-[13px]" style={muted}>{text.none}</p>
  return (
    <div className="space-y-4">
      {classes.filter(c => groups.some(g => g.cls === c.id)).map(c => (
        <section key={c.id}>
          <p className="text-[12px] font-semibold uppercase tracking-wide mb-1.5" style={c.id === 'award' ? { color: AWARD } : muted}>{c.label}</p>
          <div className="space-y-2">
            {groups.filter(g => g.cls === c.id).map((g, i) => (
              <div key={i}>
                {g.prog && (i === 0 || groups.filter(x => x.cls === c.id)[i - 1].prog !== g.prog)
                  ? <p className="text-[13px] font-semibold mb-1">{g.prog}</p> : null}
                <Flow g={g} t={text} />
              </div>))}
          </div>
        </section>))}
    </div>)
}

export default function FyFundMoves({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  return (
    <figure aria-label={alt}>
      <p className="text-[13.5px]"><span className="font-semibold tabular-nums">{y.t}</span> <span style={secondary}>{t.lead} {y.fy}</span>
        <span className="tabular-nums" style={secondary}>, {y.n} {t.entries}</span>
        {y.n_award ? <> · <span className="font-semibold tabular-nums" style={{ color: AWARD }}>{y.t_award}</span> <span style={secondary}>{t.award_lead}</span></> : null}
        {y.t_undone ? <> · <span className="font-semibold tabular-nums" style={{ color: 'var(--thread-3)' }}>{y.t_undone}</span> <span style={secondary}>{t.undone_lead}</span></> : null}</p>
      <p className="text-[12.5px] mt-1 mb-3" style={muted}>{t.what} {t.open}.</p>
      <MoveGroups groups={y.groups} classes={d.classes} text={t} />
    </figure>)
}
