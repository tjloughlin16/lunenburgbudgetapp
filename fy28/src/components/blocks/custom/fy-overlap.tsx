/** OVERLAP WITH THE SCHOOL BUDGET (fy-breakdown). TJ, 27 October 2026: "these other sources of
 *  funds are complimenting or supplementing some aspects of the school budget and we can tell by
 *  the overlap ... a chart or some viz that shows how much overlap there is".
 *
 *  The page's year. Other funds' money in bands, strongest overlap first -- the same bills, the
 *  same vendor, the same function code -- then cannot tell, then separate; bills re-charged BACK
 *  to the school budget drawn left of zero. In all, then by who paid, on one scale. Then, on the
 *  school lines other funds paid toward, the share of what those lines cost that they paid.
 *  Overlap only: whether a dollar supplemented the school budget or supplanted it is not in any
 *  ledger, and the block's "what it means" says so.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

type B = 'bills' | 'payee' | 'code' | 'unknown' | 'separate' | 'back'
type Pack = { n: Record<B, number>; t: Record<B, string> }
type Year = { fy: string; all: Pack; whole: string; over: string; over_pct: string
  groups: (Pack & { id: string; total: string })[]
  lines: { n: string; gf: string; other: string; cost: string; gf_v: number; other_v: number; share: string } }
type Data = { years: Year[]; bands: { id: B; label: string; means: string }[]; groups: { id: string; label: string }[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const hatch = (c: string) => `repeating-linear-gradient(135deg, ${c} 0 3px, transparent 3px 6px)`
// one hue, strongest overlap darkest; then the two kinds of no overlap in greys
const FILL: Record<B, string> = {
  bills: 'var(--thread-2)',
  payee: 'color-mix(in srgb, var(--thread-2) 65%, transparent)',
  code: 'color-mix(in srgb, var(--thread-2) 35%, transparent)',
  unknown: hatch('var(--text-muted)'),
  separate: 'color-mix(in srgb, var(--text-muted) 35%, transparent)',
  back: hatch('var(--thread-1)'),
}
const ORDER: B[] = ['bills', 'payee', 'code', 'unknown', 'separate']

function Bar({ p, lo, hi, total }: { p: Pack; lo: number; hi: number; total?: string }) {
  const pc = (v: number) => ((v - lo) / (hi - lo)) * 100
  let x = 0
  return (
    <div className="flex items-center gap-2 w-full sm:flex-1 min-w-0">
      <div className="relative h-6 flex-1 min-w-0">
        <div className="absolute inset-y-0 w-px" style={{ left: `${pc(0)}%`, background: 'var(--text-secondary)' }} />
        {p.n.back < -0.5 ? (
          <div title={p.t.back} className="absolute top-0.5 bottom-0.5"
            style={{ left: `${pc(p.n.back)}%`, width: `${pc(0) - pc(p.n.back)}%`, background: FILL.back }} />) : null}
        {ORDER.map(b => {
          const v = Math.max(0, p.n[b])
          if (v < 0.5) return null
          const el = <div key={b} title={p.t[b]} className="absolute top-0.5 bottom-0.5"
            style={{ left: `${pc(x)}%`, width: `max(2px, ${pc(x + v) - pc(x)}%)`, background: FILL[b], borderRight: '1px solid var(--surface-1, #fff)' }} />
          x += v
          return el
        })}
      </div>
      {total ? <span className="text-[12.5px] tabular-nums font-semibold whitespace-nowrap w-24 text-right">{total}</span> : null}
    </div>)
}

export default function FyOverlap({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const label = Object.fromEntries(d.groups.map(g => [g.id, g.label]))
  const pos = (p: Pack) => ORDER.reduce((s, b) => s + Math.max(0, p.n[b]), 0)
  const lo = Math.min(0, y.all.n.back) * 1.04, hi = pos(y.all) * 1.02
  const L = y.lines
  const share = L.other_v / (L.gf_v + L.other_v || 1)
  return (
    <figure aria-label={alt}>
      <p className="text-[13px] font-semibold">{t.h_bands}</p>
      <p className="mt-1"><span className="text-[26px] font-semibold tabular-nums">{y.over}</span>
        <span className="text-[14px]" style={secondary}> {t.of} {y.whole} · {y.over_pct} {t.overlap}</span></p>
      <div className="mt-2 flex flex-col sm:flex-row sm:items-center gap-x-3">
        <div className="sm:w-48 shrink-0 text-[13px]">{t.all}</div>
        <Bar p={y.all} lo={lo} hi={hi} total={y.whole} />
      </div>
      <div className="flex text-[11.5px] sm:pl-[12.75rem] sm:pr-[6.5rem] mt-0.5" style={muted}>
        <span className="flex-1">{t.strong} →</span><span>→ {t.none_}</span>
      </div>
      <ul className="mt-2 grid gap-x-6 gap-y-1.5 sm:grid-cols-2 text-[12.5px]">
        {[...ORDER, ...(y.all.n.back < -0.5 ? ['back' as B] : [])].map(b => {
          const band = d.bands.find(x => x.id === b)
          return (
            <li key={b} className="flex gap-2">
              <span className="inline-block w-3 h-3 mt-0.5 shrink-0 rounded-[2px]" style={{ background: FILL[b] }} />
              <span><span className="font-semibold">{band ? band.label : t.back}</span> <span className="tabular-nums">{y.all.t[b]}</span>
                <span className="block text-[11.5px] leading-snug" style={muted}>{band ? band.means : t.back_means}</span></span>
            </li>)
        })}
      </ul>

      <p className="text-[13px] font-semibold mt-5 mb-1">{t.h_groups}</p>
      <div className="space-y-1.5">
        {y.groups.map(g => (
          <div key={g.id} className="flex flex-col sm:flex-row sm:items-center gap-x-3">
            <div className="sm:w-48 shrink-0 text-[13px]">{label[g.id]}</div>
            <Bar p={g} lo={lo} hi={hi} total={g.total} />
          </div>))}
      </div>

      <p className="text-[13px] font-semibold mt-5 mb-1">{t.h_lines}</p>
      <p className="text-[13px]" style={secondary}>{L.n} {t.lines_a} · {L.cost}</p>
      <div className="flex h-6 mt-1 rounded-sm overflow-hidden">
        <div title={`${t.school}: ${L.gf}`} style={{ width: `${(1 - share) * 100}%`, background: 'var(--thread-1)' }} />
        <div title={`${t.other}: ${L.other}`} style={{ width: `${share * 100}%`, background: FILL.bills }} />
      </div>
      <div className="flex justify-between text-[12.5px] mt-0.5 gap-3">
        <span>{t.school} <span className="tabular-nums font-semibold">{L.gf}</span></span>
        <span className="text-right">{t.other} <span className="tabular-nums font-semibold">{L.other}</span> · {L.share} {t.share}</span>
      </div>
    </figure>)
}
