/** EVERY WEEK OF THE YEAR (fy-breakdown): the line popup's weekly chart, for every school line
 *  at once. TJ, 27 October 2026: "the SAME chart, but across the whole year, across every spend,
 *  for every line? Maybe it will show the recharges and big weeks of the year".
 *
 *  The page's fiscal year (fy-year.ts), Monday-to-Sunday bars, stacked by who paid or by kind of posting
 *  (payroll runs every other week would otherwise hide every other spike); bills re-charged off
 *  the school budget below the line. Hover or tap a week for its largest entries.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useEffect, useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

type Top = { line: string; what: string; payee: string; fund: string; text: string }
type Week = { w: string; label: string; f: [string, number][]; k: [string, number][]; rc: number; rb: number; t: string; t_rc: string; t_rb: string; top: Top[] }
type Year = { fy: string; a0: string; a1: string; weeks: Week[]; total: string; recharged: string; back: string }
type Data = { years: Year[]; payers: { id: string; label: string }[]; kinds: { id: string; label: string }[]
  text: Record<'by_fund' | 'by_kind' | 'clear' | 'recharge' | 'back' | 'spent' | 'recharged' | 'back_total' | 'biggest' | 'pick' | 'note', string> }

const COLOURS = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-5)', 'var(--thread-4)', 'var(--thread-3)', 'var(--thread-6, var(--text-secondary))']
const RC = 'var(--text-muted)', RB = 'var(--grid)'
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

export default function FyYearWeeks({ data, alt }: CustomProps) {
  const d = data as Data
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)                     // the page's year (fy-year.ts)
  const yi = Math.max(0, fys.indexOf(fy))
  const [kind, setKind] = useState(false)
  const [hot, setHot] = useState<number | null>(null)
  const [held, setHeld] = useState<number | null>(null)
  const y = d.years[yi]
  const groups = kind ? d.kinds : d.payers
  const colour = Object.fromEntries(groups.map((g, i) => [g.id, COLOURS[i % COLOURS.length]]))
  const parts = (w: Week) => (kind ? w.k : w.f)
  const W = 1000, H = 300, PAD = 8, AX = 18
  const day = (iso: string) => Date.parse(iso + 'T00:00:00Z') / 864e5
  const d0 = day(y.a0), d1 = day(y.a1) + 1
  const x = (iso: string) => PAD + ((day(iso) - d0) / (d1 - d0)) * (W - 2 * PAD)
  // one scale for every year, so a bigger week looks bigger whichever year is picked
  const up = Math.max(1, ...d.years.flatMap(v => v.weeks.map(w => w.rb + w.f.reduce((a, [, n]) => a + Math.max(0, n), 0))))
  const down = Math.max(0, ...d.years.flatMap(v => v.weeks.map(w => -Math.min(0, w.rc) + w.f.reduce((a, [, n]) => a + Math.max(0, -n), 0))))
  const k = (H - AX - 2 * PAD) / (up + down)
  const zero = PAD + up * k
  const bw = Math.max(2, (7 / (d1 - d0)) * (W - 2 * PAD) - 2)
  const months: string[] = []
  for (let m = new Date(y.a0 + 'T00:00:00Z'); m <= new Date(y.a1 + 'T00:00:00Z'); m.setUTCMonth(m.getUTCMonth() + 1, 1)) {
    months.push(new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth(), 1)).toISOString().slice(0, 10))
  }
  // Hover previews a week; a click or tap pins it. A pin clears by clicking the bar again, the
  // chart's empty space, the Clear button or Escape (TJ: "i dont know how to unhover the
  // timeline"). Touch never hovers: a tap is a pin, so nothing sticks without a way out.
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') { setHeld(null); setHot(null) } }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])
  useEffect(() => { setHeld(null); setHot(null) }, [fy])
  const tip = hot ?? held
  const wk = tip === null ? null : y.weeks[tip]
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5 items-center">
        <Chip on={!kind} onClick={() => setKind(false)}>{d.text.by_fund}</Chip>
        <Chip on={kind} onClick={() => setKind(true)}>{d.text.by_kind}</Chip>
      </div>
      <p className="mt-2 text-[13.5px]"><span className="tabular-nums font-semibold">{y.total}</span> <span style={secondary}>{d.text.spent}</span>
        {y.recharged ? <> · <span className="tabular-nums font-semibold">{y.recharged}</span> <span style={secondary}>{d.text.recharged}</span></> : null}
        {y.back ? <> · <span className="tabular-nums font-semibold">{y.back}</span> <span style={secondary}>{d.text.back_total}</span></> : null}</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] mt-1.5" style={secondary}>
        {groups.filter(g => y.weeks.some(w => parts(w).some(([id]) => id === g.id))).map(g => (
          <span key={g.id} className="inline-flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: colour[g.id] }} />{g.label}</span>))}
        {y.weeks.some(w => w.rc) ? <span className="inline-flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: RC }} />{d.text.recharge}</span> : null}
        {y.weeks.some(w => w.rb) ? <span className="inline-flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: RB, outline: `0.5px solid ${RC}` }} />{d.text.back}</span> : null}
      </div>
      <div className="relative mt-1">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block" role="img" aria-label={alt} onPointerLeave={() => setHot(null)}>
          <rect x={0} y={0} width={W} height={H} fill="transparent" onClick={() => { setHeld(null); setHot(null) }} />
          <line x1={PAD} x2={W - PAD} y1={zero} y2={zero} stroke="var(--grid)" />
          {months.filter(m => m >= y.a0).map(m => (
            <text key={m} x={x(m) + 2} y={H - 4} fontSize={12} fill="var(--text-muted)">{MONTH[Number(m.slice(5, 7)) - 1]}</text>))}
          {y.weeks.map((w, i) => {
            let top = zero, bot = zero
            const segs = groups.map(g => parts(w).find(([id]) => id === g.id)).filter(Boolean) as [string, number][]
            return (
              <g key={w.w} opacity={tip === null || tip === i ? 1 : 0.35} style={{ cursor: 'pointer' }}
                onPointerEnter={e => { if (e.pointerType === 'mouse') setHot(i) }}
                onClick={() => { setHot(null); setHeld(h => (h === i ? null : i)) }}>
                <rect x={x(w.w)} y={PAD} width={bw} height={H - AX - 2 * PAD} fill="transparent" />
                {segs.map(([id, v]) => {
                  const h = Math.abs(v) * k
                  if (v < 0) { const y0 = bot; bot += h; return <rect key={id} x={x(w.w)} y={y0} width={bw} height={h} fill={colour[id]} /> }
                  top -= h
                  return <rect key={id} x={x(w.w)} y={top} width={bw} height={h} fill={colour[id]} />
                })}
                {w.rc ? <rect x={x(w.w)} y={bot} width={bw} height={Math.abs(w.rc) * k} fill={RC} /> : null}
                {w.rb ? <rect x={x(w.w)} y={top - w.rb * k} width={bw} height={w.rb * k} fill={RB} stroke={RC} strokeWidth={0.5} /> : null}
              </g>)
          })}
        </svg>
      </div>
      <div className="mt-2 text-[13px] min-h-[3rem]">
        {wk ? (
          <div className="max-w-3xl">
            <p className="flex justify-between gap-3 items-baseline"><span><span className="font-semibold">{wk.label}</span> · <span className="tabular-nums font-semibold">{wk.t}</span>
              {wk.t_rc ? <span style={secondary}> · {d.text.recharge} <span className="tabular-nums">{wk.t_rc}</span></span> : null}
              {wk.t_rb ? <span style={secondary}> · {d.text.back} <span className="tabular-nums">{wk.t_rb}</span></span> : null}</span>
              {held !== null ? <button type="button" className="text-[12.5px] px-2 py-0.5 rounded border shrink-0" style={{ borderColor: 'var(--grid)' }}
                onClick={() => { setHeld(null); setHot(null) }}>{d.text.clear} ✕</button> : null}</p>
            <p className="text-[12px] mt-1" style={muted}>{d.text.biggest}</p>
            <ul className="mt-0.5">
              {wk.top.map((e, j) => (
                <li key={j} className="flex justify-between gap-3 py-0.5 border-b" style={{ borderColor: 'var(--grid)' }}>
                  <span className="min-w-0">{e.line}<span className="block text-[12px]" style={secondary}>{e.what}{e.payee ? ` · ${e.payee}` : ''} · {e.fund}</span></span>
                  <span className="tabular-nums font-semibold whitespace-nowrap">{e.text}</span></li>))}
            </ul>
          </div>) : <p style={muted}>{d.text.pick}</p>}
      </div>
      <figcaption className="text-[12.5px] mt-2 leading-snug max-w-3xl" style={muted}>{d.text.note}</figcaption>
    </figure>
  )
}
