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
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'
import { PAYER, hatch, Row } from './fy-shared'

type Other = { id: string; start: number; later: number; unmatched: number; t: Record<'start' | 'later' | 'paid' | 'unmatched' | 'all', string> }
type Year = { fy: string; book: string | null; book_line: string | null; raw: string[]; unread: boolean
  gf: { budget: number; before: number; off: number; on: number; spent: number; left: number; early: number; unspent: number
    t: Record<'budget' | 'before' | 'off' | 'on' | 'spent' | 'left' | 'under' | 'voted' | 'transfers' | 'carried' | 'early' | 'own' | 'unspent' | 'used', string> }
  cb: { plan: number | null; paid: number; unspent: number; t: { plan: string | null; paid: string; unspent: string; used: string | null; gross: string; net: string; diff: string | null } }
  others: Other[]; others_t: Record<'start' | 'later' | 'paid' | 'unmatched' | 'all', string>
  totals: { plan: number; happened: number; unmatched: number; unspent: number; t: { plan: string; happened: string; beyond: string; unspent: string } } }
type Data = { years: Year[]; groups: { id: string; label: string }[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

/** A bar from zero: its parts side by side, and UNDER IT A VERTICAL LABEL FOR EACH FUND (TJ, 28
 *  October 2026: "show the 'what happened' chart without a huge long running legend, and instead
 *  use vertical labels for the funds"). Each label hangs from its segment's middle on a leader
 *  line, so the eye goes from the colour straight to the name. A fund's parts on and off a school
 *  line share one label (`group`), its value the two added with the hatched part named. Labels
 *  too close to fit are spread apart and their leaders bend, never overlap. */
type Part = { name: string; value: number; text: string; fill: string; outline?: boolean; group?: string }
// UNSPENT is OUTLINED, never filled: money allocated to the year and not spent is not spending,
// and a filled bar would read as some
const outlined = (c: string) => ({ background: 'transparent', border: `1.5px dashed ${c}` })
type Label = { name: string; text: string; swatch: React.CSSProperties; title: string; mid: number; parts: Part[] }
const GAP = 4, DROP = 18
const usd = (v: number) => '$' + Math.round(v).toLocaleString('en-US')

function labels(shown: Part[], max: number): Label[] {
  const out: (Label & { from: number; to: number; parts: Part[] })[] = []
  let at = 0
  for (const p of shown) {
    const last = out[out.length - 1]
    if (p.group && last && last.parts[0].group === p.group) { last.parts.push(p); last.to = at + p.value }
    else out.push({ name: p.group ?? p.name, text: '', title: '', mid: 0, from: at, to: at + p.value, parts: [p],
      swatch: p.outline ? outlined(p.fill) : { background: p.fill } })
    at += p.value
  }
  return out.map(l => ({ ...l, mid: ((l.from + l.to) / 2 / max) * 100,
    // ONE LINE OF VALUE: the fund's total. The split on and off a school line is in the hover,
    // and the key under the bar says what the hatching is
    text: l.parts.length > 1 ? usd(l.parts.reduce((a, p) => a + p.value, 0)) : l.parts[0].text,
    title: l.parts.map(p => `${p.name}: ${p.text}`).join('\n') }))
}

function Absolute({ parts, max, total, hatched }: { parts: Part[]; max: number; total: string; hatched?: string }) {
  const shown = parts.filter(p => p.value > 0.5)
  const ls = labels(shown, max)
  const box = useRef<HTMLDivElement>(null)
  const refs = useRef<(HTMLDivElement | null)[]>([])
  const [geo, setGeo] = useState<{ w: number; xs: number[]; h: number; fit: boolean } | null>(null)
  // MEASURED, not guessed: the row's width and each label's own, then a left-to-right pass that
  // keeps every label clear of the one before and a right-to-left pass that keeps the last ones
  // inside the row
  useLayoutEffect(() => {
    const el = box.current
    if (!el) return
    const place = () => {
      const w = el.clientWidth
      const ws = ls.map((_, i) => refs.current[i]?.offsetWidth ?? 0)
      const xs = ls.map((l, i) => (l.mid / 100) * w - ws[i] / 2)
      for (let i = 0; i < xs.length; i++) xs[i] = Math.max(xs[i], i ? xs[i - 1] + ws[i - 1] + GAP : 0)
      for (let i = xs.length - 1; i >= 0; i--) xs[i] = Math.min(xs[i], i < xs.length - 1 ? xs[i + 1] - ws[i] - GAP : w - ws[i])
      for (let i = 0; i < xs.length; i++) xs[i] = Math.max(xs[i], i ? xs[i - 1] + ws[i - 1] + GAP : 0)
      const h = Math.max(0, ...ls.map((_, i) => refs.current[i]?.offsetHeight ?? 0))
      // A PHONE CANNOT HOLD THEM SIDE BY SIDE: past the row's width the labels become a wrapped
      // list under the bar instead, the leaders dropped (a leader to a label off its segment
      // would point nowhere)
      const fit = ws.reduce((a, x) => a + x, 0) + GAP * (ws.length - 1) <= w
      setGeo(g => g && g.w === w && g.h === h && g.fit === fit && g.xs.every((x, i) => Math.abs(x - xs[i]) < 0.5) && g.xs.length === xs.length ? g : { w, xs, h, fit })
    }
    place()
    const ro = new ResizeObserver(place)
    ro.observe(el)
    return () => ro.disconnect()
  })
  return (
    <div className="w-full sm:flex-1 min-w-0 shrink-0">
      <div className="flex items-start gap-2">
        <div ref={box} className="relative flex-1 min-w-0">
          <div className="relative h-6">
            {shown.reduce<{ at: number; el: React.ReactNode[] }>((acc, p, i) => {
              acc.el.push(<div key={i} title={`${p.name}: ${p.text}`} className="absolute top-0.5 bottom-0.5"
                style={{ left: `${(acc.at / max) * 100}%`, width: `max(2px, ${(p.value / max) * 100}%)`,
                  ...(p.outline ? outlined(p.fill) : { background: p.fill, borderRight: '1px solid var(--surface-1, #fff)' }) }} />)
              acc.at += p.value
              return acc
            }, { at: 0, el: [] }).el}
          </div>
          <div className="relative overflow-hidden" style={{ height: geo ? (geo.fit ? DROP + geo.h : 0) : DROP + 120 }}>
            {geo?.fit ? (
              <svg aria-hidden className="absolute inset-x-0 top-0 overflow-visible" width={geo.w} height={DROP}>
                {ls.map((l, i) => {
                  const m = (l.mid / 100) * geo.w, c = geo.xs[i] + (refs.current[i]?.offsetWidth ?? 0) / 2
                  return <path key={i} d={`M${m},0 V5 L${c},${DROP - 4} V${DROP}`} fill="none" stroke="var(--text-muted)" strokeWidth={1} />
                })}
              </svg>) : null}
            {ls.map((l, i) => (
              <div key={i} ref={e => { refs.current[i] = e }} title={l.title}
                className="absolute flex flex-col items-start gap-x-0.5 text-[11.5px] leading-tight whitespace-nowrap"
                style={{ top: DROP, left: geo ? geo.xs[i] : 0, visibility: geo?.fit ? 'visible' : 'hidden',
                  writingMode: 'vertical-lr', color: 'var(--text-secondary)' }}>
                <span className="inline-flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-[1px] shrink-0" style={l.swatch} />{l.name}</span>
                <span className="tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>{l.text}</span>
              </div>))}
          </div>
        </div>
        <span className="text-[12.5px] tabular-nums font-semibold whitespace-nowrap leading-6">{total}</span>
      </div>
      {geo && !geo.fit ? (
        <p className="text-[11.5px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
          {ls.map((l, i) => <span key={i} title={l.title} className="inline-flex items-center gap-1 mr-3 whitespace-nowrap">
            <span className="inline-block w-2 h-2 rounded-[1px]" style={l.swatch} />{l.name} <span className="tabular-nums">{l.text}</span></span>)}
        </p>) : null}
      {hatched && ls.some(l => l.parts.length > 1) ? (
        <p className="text-[11.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
          <span className="inline-block w-2.5 h-2.5 align-[-1px] mr-1 rounded-[1px]" style={{ background: hatch('var(--text-muted)') }} />{hatched}</p>) : null}
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
  const g = y.gf

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
            {/* UNSPENT AT THE END OF WHAT HAPPENED, outlined, after every dollar spent (TJ, 27
                October 2026, picking this over the plan bar: "im not sure that makes sense") */}
            <Row label={t.a_happened} sub={`${t.a_happened_sub} · ${y.totals.t.beyond} ${t.a_beyond}${y.totals.unspent > 0.5 ? ` · ${t.a_unspent_sub}` : ''}`}>
              <Absolute max={max} total={y.totals.t.happened} hatched={t.hatched_part} parts={[
                { name: t.a_gf_spent, value: g.spent - g.early, text: g.t.own, fill: PAYER.gf },
                { name: t.a_gf_early, value: g.early, text: g.t.early, fill: hatch(PAYER.gf) },
                { name: t.a_cb_paid, value: y.cb.paid, text: y.cb.t.paid, fill: cbFill },
                ...y.others.flatMap(o => [
                  { name: label[o.id], value: o.start + o.later, text: o.t.paid, fill: o.id === 'cb' ? hatch(PAYER.cb) : PAYER[o.id], group: label[o.id] },
                  { name: `${label[o.id]}, ${t.on_no_line}`, value: o.unmatched, text: o.t.unmatched, fill: hatch(PAYER[o.id]), group: label[o.id] }]),
                { name: t.a_gf_unspent, value: g.unspent, text: g.t.unspent, fill: PAYER.gf, outline: true },
                { name: t.a_cb_unspent, value: y.cb.unspent, text: y.cb.t.unspent, fill: PAYER.cb, outline: true }]} />
            </Row>
            <p className="text-[11.5px] sm:pl-[14.75rem]" style={muted}>{t.a_unspent_note}</p>
          </div>)
      })()}
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
              ['r', t.counted, (y: Year) => y.cb.t.plan ?? (y.unread ? t.not_read : t.none)],
              ['r', t.collab_net, (y: Year) => y.cb.t.net],
              ['h', t.h_gf],
              ['r', t.before, (y: Year) => y.gf.t.before],
              ['r', t.under, (y: Year) => y.gf.t.under],
              ['r', t.lg_off, (y: Year) => y.gf.t.off],
              ['r', t.lg_on, (y: Year) => y.gf.t.on],
              ['r', t.spent, (y: Year) => y.gf.t.spent],
              ['b', t.left_row, (y: Year) => y.gf.t.left],
              ['h', t.r_cb],
              ['r', t.counted, (y: Year) => y.cb.t.plan ?? (y.unread ? t.not_read : t.none)],
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
        {y.book ? <p className="mt-1"><a href={y.book} className="underline">{t.book}</a>
          <span style={muted}>, {t.line} {y.book_line}</span></p> : <p className="mt-1" style={muted}>{t.unread}</p>}
        {y.raw.map((r, i) => <code key={i} className="block text-[11.5px] whitespace-pre-wrap" style={secondary}>{r}</code>)}
      </details>
    </figure>)
}
