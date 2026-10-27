/** THE PLAN AGAINST WHAT HAPPENED (fy-breakdown, level 1). TJ, 27 October 2026: "did the general
 *  fund pay for what we said it needed to pay for... or did grants end up covering it, or
 *  relieving it", and, on collaborative tuition being voted net of the circuit breaker, "compare
 *  what happened with the general fund and cb to make sure it matches the plan (visually)".
 *
 *  TWO CHARTS. First IN DOLLARS, every bar from zero (TJ: "i wanted to see the absolute values"):
 *  the plan (the budget, and the circuit breaker the book counted on), and every school dollar
 *  spent, by who paid (TJ: "how far beyond the budget spending went, and from where"). Money on
 *  no school line is in it, hatched in its payer's colour: school spending, line unknown. Then the
 *  DIFFERENCE ONLY, kept to put the first in context (TJ: "add another chart so i can put this
 *  one in context without removing it first"), where every bar starts at the plan. Left of it is
 *  less than the plan, right of it more:
 *   - the school general fund, against its budget: what it spent before any re-charges, then the
 *     bills re-charged off it and back onto it, ending at what it spent (less than the budget is
 *     what was left);
 *   - the circuit breaker on collaborative tuition, against the offset the book printed under
 *     that line (in a year whose book printed none, all of it is beyond the plan);
 *   - other funds, which no book printed as part of the plan, by who paid.
 *  One year, the page's, on its own scale.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

type Other = { id: string; start: number; later: number; unmatched: number; t: Record<'start' | 'later' | 'paid' | 'unmatched' | 'all', string> }
type Year = { fy: string; book: string; book_line: string; raw: string[]
  gf: { budget: number; before: number; off: number; on: number; spent: number; left: number; early: number; unspent: number
    t: Record<'budget' | 'before' | 'off' | 'on' | 'spent' | 'left' | 'under' | 'voted' | 'transfers' | 'carried' | 'early' | 'own' | 'unspent', string> }
  cb: { plan: number | null; paid: number; unspent: number; t: { plan: string | null; paid: string; unspent: string; gross: string; net: string; diff: string | null } }
  others: Other[]; others_t: Record<'start' | 'later' | 'paid' | 'unmatched' | 'all', string>
  totals: { plan: number; happened: number; unmatched: number; unspent: number; t: { plan: string; happened: string; beyond: string; unspent: string } } }
type Data = { years: Year[]; groups: { id: string; label: string }[]; text: Record<string, string> }

// the weekly chart's colours, by payer, so a fund is one colour across the page
const PAYER = { gf: 'var(--thread-1)', idea: 'var(--thread-2)', grants: 'var(--thread-5)', cb: 'var(--thread-4)',
  fees: 'var(--thread-3)', other: 'var(--thread-6, var(--text-secondary))' } as Record<string, string>
const RC = 'var(--text-muted)'
// re-charged back: a pale solid, apart from capital's dark grey and the hatched step off
const BACK = 'color-mix(in srgb, var(--text-muted) 45%, transparent)'
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const hatch = (c: string) => `repeating-linear-gradient(135deg, ${c} 0 3px, transparent 3px 6px)`

type Seg = { from: number; to: number; fill: string; title: string; border?: string; lane?: number }

// `lanes`: a WATERFALL's steps each on their own lane, top to bottom, so a step back does not
// paint over the step before it (the general fund: spent before re-charges, re-charged off,
// re-charged back on)
function Track({ segs, lo, hi, end, endText, lanes = 1 }: { segs: Seg[]; lo: number; hi: number; end?: number; endText?: string; lanes?: number }) {
  const pc = (v: number) => ((v - lo) / (hi - lo)) * 100
  const zero = pc(0)
  const lane = (i = 0) => lanes === 1 ? { top: 4, bottom: 4 } : { top: `${4 + (i * 92) / lanes}%`, height: `${92 / lanes - 4}%` }
  return (
    // w-full, and flex-1 only beside the label: in the phone's column layout flex-1 would give
    // the track a zero basis and no height
    <div className={`relative ${lanes > 1 ? 'h-10' : 'h-6'} w-full sm:flex-1 min-w-0 shrink-0`}>
      <div className="absolute inset-y-0 w-px" style={{ left: `${zero}%`, background: 'var(--text-secondary)' }} />
      {segs.filter(s => Math.abs(s.to - s.from) > 0.5).map((s, i) => {
        const a = pc(Math.min(s.from, s.to)), b = pc(Math.max(s.from, s.to))
        return <div key={i} title={s.title} className="absolute rounded-[2px]"
          style={{ ...lane(s.lane), left: `${a}%`, width: `max(2px, ${b - a}%)`, background: s.fill, border: s.border }} />
      })}
      {end !== undefined ? (
        <div className="absolute top-0 bottom-0 w-0.5" style={{ left: `${pc(end)}%`, background: 'var(--text-primary)' }} />) : null}
      {end !== undefined && endText ? (
        // on whichever side of the marker has more room, so it never runs off a phone's edge
        <span className="absolute top-1/2 -translate-y-1/2 text-[11.5px] tabular-nums font-semibold whitespace-nowrap px-1 rounded-sm"
          style={{ background: 'var(--surface-1, var(--surface-2))', ...(pc(end) > 50 ? { right: `${100 - pc(end)}%`, marginRight: 3 } : { left: `${pc(end)}%`, marginLeft: 3 }) }}>{endText}</span>) : null}
    </div>)
}

/** A bar from zero: its parts side by side, and under it each part's name and value, since a
 *  small part is too thin to carry its own label. */
type Part = { name: string; value: number; text: string; fill: string; outline?: boolean }
// UNSPENT is OUTLINED, never filled: money allocated to the year and not spent is not spending,
// and a filled bar would read as some
const outlined = (c: string) => ({ background: 'transparent', border: `1.5px dashed ${c}` })
function Absolute({ parts, max, total }: { parts: Part[]; max: number; total: string }) {
  const shown = parts.filter(p => p.value > 0.5)
  return (
    <div className="w-full sm:flex-1 min-w-0 shrink-0">
      <div className="flex items-center gap-2">
        <div className="relative h-6 flex-1 min-w-0">
          {shown.reduce<{ at: number; el: React.ReactNode[] }>((acc, p, i) => {
            acc.el.push(<div key={i} title={`${p.name}: ${p.text}`} className="absolute top-0.5 bottom-0.5"
              style={{ left: `${(acc.at / max) * 100}%`, width: `max(2px, ${(p.value / max) * 100}%)`,
                ...(p.outline ? outlined(p.fill) : { background: p.fill, borderRight: '1px solid var(--surface-1, #fff)' }) }} />)
            acc.at += p.value
            return acc
          }, { at: 0, el: [] }).el}
        </div>
        <span className="text-[12.5px] tabular-nums font-semibold whitespace-nowrap">{total}</span>
      </div>
      <p className="text-[11.5px] leading-snug mt-0.5" style={secondary}>
        {shown.map((p, i) => <span key={i} className="inline-flex items-center gap-1 mr-3 whitespace-nowrap">
          <span className="inline-block w-2 h-2 rounded-[1px]" style={p.outline ? outlined(p.fill) : { background: p.fill }} />{p.name} <span className="tabular-nums">{p.text}</span></span>)}
      </p>
    </div>)
}

function Row({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-x-3 py-1">
      <div className="sm:w-56 shrink-0 text-[13px] leading-tight">{label}
        {sub ? <span className="block text-[11.5px]" style={muted}>{sub}</span> : null}</div>
      {children}
    </div>)
}

export default function FyPlan({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  // ONE YEAR AT A TIME (TJ, 27 October 2026: "i want each of these charts and tables to be a
  // single FY... we can add comparison page later"): the page's year, on its own scale
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const label = Object.fromEntries(d.groups.map(g => [g.id, g.label]))
  const g = y.gf, a = g.before - g.budget, b = a - g.off, c = b + g.on
  const cbv = y.cb.plan === null ? y.cb.paid : y.cb.paid - y.cb.plan
  let x = 0
  const others: Seg[] = []
  for (const o of y.others) {
    for (const [v, part, text] of [[o.start, t.from_start, o.t.start], [o.later, t.later, o.t.later], [o.unmatched, t.on_no_line, o.t.unmatched]] as const) {
      if (v > 0.5) {
        others.push({ from: x, to: x + v, fill: part === t.on_no_line || o.id === 'cb' ? hatch(PAYER[o.id]) : PAYER[o.id],
          title: `${label[o.id]}, ${part}: ${text}` })
        x += v
      }
    }
  }
  const lo0 = Math.min(0, a, b, c, cbv), hi0 = Math.max(0, a, b, c, cbv, x)
  const pad = (hi0 - lo0) * 0.04
  const lo = lo0 - pad, hi = hi0 + pad

  return (
    <figure aria-label={alt}>
      <p className="text-[13px] font-semibold mt-3 mb-1">{t.h_abs}</p>
      {(() => {
        const max = Math.max(y.totals.plan, y.totals.happened + y.totals.unspent)
        const cbFill = y.cb.plan === null ? hatch(PAYER.cb) : PAYER.cb
        return (
          <div className="space-y-1.5">
            <Row label={t.a_plan} sub={t.a_plan_sub}>
              <Absolute max={max} total={y.totals.t.plan} parts={[
                { name: t.a_gf_budget, value: g.budget, text: g.t.budget, fill: 'color-mix(in srgb, var(--thread-1) 55%, transparent)' },
                ...(y.cb.plan !== null && y.cb.t.plan ? [{ name: t.a_cb_plan, value: y.cb.plan, text: y.cb.t.plan,
                  fill: 'color-mix(in srgb, var(--thread-4) 55%, transparent)' }] : [])]} />
            </Row>
            <Row label={t.a_happened} sub={`${t.a_happened_sub} · ${y.totals.t.beyond} ${t.a_beyond}${y.totals.unspent > 0.5 ? ` · ${t.a_unspent_sub}` : ''}`}>
              {/* the general fund's spent and unspent first, then the circuit breaker's, so each
                  ends where its part of the plan above ends */}
              <Absolute max={max} total={y.totals.t.happened} parts={[
                { name: t.a_gf_spent, value: g.spent - g.early, text: g.t.own, fill: PAYER.gf },
                { name: t.a_gf_early, value: g.early, text: g.t.early, fill: hatch(PAYER.gf) },
                { name: t.a_gf_unspent, value: g.unspent, text: g.t.unspent, fill: PAYER.gf, outline: true },
                { name: t.a_cb_paid, value: y.cb.paid, text: y.cb.t.paid, fill: cbFill },
                { name: t.a_cb_unspent, value: y.cb.unspent, text: y.cb.t.unspent, fill: PAYER.cb, outline: true },
                ...y.others.flatMap(o => [
                  { name: label[o.id], value: o.start + o.later, text: o.t.paid, fill: o.id === 'cb' ? hatch(PAYER.cb) : PAYER[o.id] },
                  { name: `${label[o.id]}, ${t.on_no_line}`, value: o.unmatched, text: o.t.unmatched, fill: hatch(PAYER[o.id]) }])]} />
            </Row>
            <p className="text-[11.5px] sm:pl-[14.75rem]" style={muted}>{t.a_unspent_note}</p>
          </div>)
      })()}
      <p className="text-[13px] font-semibold mt-5 mb-1">{t.h_diff}</p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] mb-2" style={secondary}>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-[2px]" style={{ background: PAYER.gf }} />{t.lg_gf}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-[2px]" style={{ background: hatch(RC) }} />{t.lg_off}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-[2px]" style={{ background: BACK }} />{t.lg_on}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-[2px]" style={{ background: PAYER.cb }} />{t.lg_cb}</span>
        {d.groups.map(g => (
          <span key={g.id} className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-[2px]"
            style={{ background: g.id === 'cb' ? hatch(PAYER.cb) : PAYER[g.id] }} />{g.label}</span>))}
      </div>
      <div className="flex text-[11.5px] sm:pl-[14.75rem]" style={muted}>
        <span className="flex-1">← {t.less}</span><span>{t.more} →</span>
      </div>
      <div className="mt-1">
        {/* what was left goes in the caption: inside the track it sat on the steps */}
        <Row label={t.r_gf} sub={`${t.budget} ${g.t.budget} · ${g.left >= 0 ? `${t.left} ${g.t.left}` : `${t.over} ${g.t.left.replace('-', '')}`}`}>
          <Track lo={lo} hi={hi} lanes={3} end={c}
            segs={[
              { from: 0, to: a, fill: PAYER.gf, lane: 0, title: `${t.before}: ${g.t.before} (${t.budget} ${g.t.budget})` },
              { from: a, to: b, fill: hatch(RC), lane: 1, title: `${t.lg_off}: ${g.t.off}` },
              { from: b, to: c, fill: BACK, lane: 2, title: `${t.lg_on}: ${g.t.on}` }]} />
        </Row>
        <Row label={t.r_cb} sub={y.cb.t.plan ? `${t.counted} ${y.cb.t.plan}` : t.none_printed}>
          <Track lo={lo} hi={hi} end={cbv}
            endText={y.cb.t.plan === null ? `${t.charged} ${y.cb.t.paid}` : `${y.cb.t.paid} ${t.charged_of} ${y.cb.t.plan}`}
            segs={[{ from: 0, to: cbv, fill: y.cb.plan === null ? hatch(PAYER.cb) : PAYER.cb,
              title: y.cb.t.plan === null ? `${t.none_printed}; ${t.charged} ${y.cb.t.paid}`
                : `${t.counted} ${y.cb.t.plan}; ${t.charged} ${y.cb.t.paid}` }]} />
        </Row>
        <Row label={t.r_other} sub={t.not_printed}>
          <Track lo={lo} hi={hi} end={x} endText={y.others_t.all} segs={others} />
        </Row>
        <p className="text-[11.5px] sm:pl-[14.75rem] mt-0.5" style={muted}>{t.unmatched_note.replace('{v}', y.others_t.unmatched)}</p>
      </div>

      {/* THE TABLE UNDER IT (TJ: "as a chart, with a supplementary table at the bottom") */}
      <div className="mt-5 overflow-x-auto">
        <table className="w-full max-w-2xl text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="px-2 py-1.5 text-left font-semibold" />
              <th className="px-2 py-1.5 text-right font-semibold">{y.fy}</th>
            </tr>
          </thead>
          <tbody>
            {([
              ['h', t.h_plan],
              ['r', t.voted, (y: Year) => y.gf.t.voted],
              ['r', t.transfers, (y: Year) => y.gf.t.transfers],
              ['r', t.carried, (y: Year) => y.gf.t.carried],
              ['b', t.budget, (y: Year) => y.gf.t.budget],
              ['r', t.collab_gross, (y: Year) => y.cb.t.gross],
              ['r', t.counted, (y: Year) => y.cb.t.plan ?? t.none],
              ['r', t.collab_net, (y: Year) => y.cb.t.net],
              ['h', t.h_gf],
              ['r', t.before, (y: Year) => y.gf.t.before],
              ['r', t.under, (y: Year) => y.gf.t.under],
              ['r', t.lg_off, (y: Year) => y.gf.t.off],
              ['r', t.lg_on, (y: Year) => y.gf.t.on],
              ['r', t.spent, (y: Year) => y.gf.t.spent],
              ['b', t.left_row, (y: Year) => y.gf.t.left],
              ['h', t.r_cb],
              ['r', t.counted, (y: Year) => y.cb.t.plan ?? t.none],
              ['r', t.charged_row, (y: Year) => y.cb.t.paid],
              ['b', t.cb_diff, (y: Year) => y.cb.t.diff === null ? t.none : `${y.cb.paid < (y.cb.plan ?? 0) ? '−' : '+'}${y.cb.t.diff}`],
              ['h', t.r_other],
              ...d.groups.map(g => ['r', g.label, (y: Year) => y.others.find(o => o.id === g.id)!.t.paid] as const),
              ['r', t.of_later, (y: Year) => y.others_t.later],
              ['b', t.other_total, (y: Year) => y.others_t.paid],
              ['r', t.unmatched_row, (y: Year) => y.others_t.unmatched],
              ['b', t.other_all, (y: Year) => y.others_t.all],
              ['h', t.a_happened],
              ['r', t.a_plan, (y: Year) => y.totals.t.plan],
              ['r', t.all_total, (y: Year) => y.totals.t.happened],
              ['b', t.beyond_row, (y: Year) => y.totals.t.beyond],
            ] as const).map((row, i) => row[0] === 'h' ? (
              <tr key={i}><td colSpan={2} className="px-2 pt-3 pb-1 text-[12px] font-semibold uppercase tracking-wide" style={muted}>{row[1]}</td></tr>
            ) : (
              <tr key={i} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1 text-left" style={row[0] === 'b' ? { fontWeight: 600 } : secondary}>{row[1]}</td>
                <td className="px-2 py-1 text-right whitespace-nowrap" style={{ fontWeight: row[0] === 'b' ? 600 : 400 }}>{row[2](y)}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <details className="mt-3 text-[12.5px]">
        <summary className="cursor-pointer font-semibold">{t.printed}</summary>
        <p className="mt-1"><a href={y.book} className="underline">{t.book}</a>
          <span style={muted}>, {t.line} {y.book_line}</span></p>
        {y.raw.map((r, i) => <code key={i} className="block text-[11.5px] whitespace-pre-wrap" style={secondary}>{r}</code>)}
      </details>
    </figure>)
}
