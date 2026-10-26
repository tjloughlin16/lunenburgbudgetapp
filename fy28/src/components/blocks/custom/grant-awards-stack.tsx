/** COMPETITIVE DOLLARS, BY DISTRICT AND GRANT (grants-others-receive).
 *
 *  TJ, 26 October 2026: "each town gets a bar, broken up by stacked bars by grant amount ...
 *  what we have now is a boolean table of what each district was granted, but not the dollar
 *  amounts to compare size wise". One bar per district, split by grant, largest first.
 *  Lunenburg is always shown, in the place its total puts it; Monty Tech sits at the
 *  foot for reference.
 *
 *  Controls: which comparison sets to show (chips), which year (both, or one), and one grant
 *  picked out from the legend -- hover previews, a click or tap holds it -- which fades the
 *  others and prints each district's amount for that grant. Hovering or tapping a BAR opens
 *  its breakdown: every grant in it with its amount, largest first, and the bar's total.
 *  The legend sits under the bars (TJ, 26 October 2026), so the bars are the first thing.
 *
 *  Every figure is formatted by build_grant_comparison_topics.py; this draws marks from the
 *  numbers and prints the given text. A phone gets the label and total on one line and the
 *  bar under it, so nothing is wider than the card. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type YKey = string
type Row = {
  name: string; kind: 'lun' | 'mt' | 'cmp'; sets: string[]
  seg: { g: number; y: YKey; v: number }[]
  val: Record<YKey, number>; tot: Record<YKey, string>
  pick: { g: number; t: Record<YKey, string>; v: Record<YKey, number> }[]
  joint: string
}
type Data = {
  years: { key: YKey; label: string }[]
  sets: { key: string; label: string }[]
  grants: { name: string }[]
  rows: Row[]
  text: { none: string; none_pick: string; all: string; sets: string; year: string; grants: string; clear: string; mt: string; bars: string; total: string }
  note: string
}

const TONES = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-3)', 'var(--thread-4)', 'var(--thread-5)']
const tone = (g: number) => TONES[g % TONES.length]
/* Twenty grants and five dependable colours: the second pass round the palette is lighter, so a
   neighbour never shares a swatch, and picking one out is what tells two of a colour apart. */
const shade = (g: number) => (Math.floor(g / TONES.length) % 2 ? 0.5 : 1)

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>
      {on ? '✓ ' : ''}{children}
    </button>
  )
}

export default function GrantAwardsStack({ data, alt }: CustomProps) {
  const d = data as Data
  const [sets, setSets] = useState<string[]>(d.sets.map(s => s.key))
  const [year, setYear] = useState<YKey>(d.years[0].key)
  const [held, setHeld] = useState<number | null>(null)
  const [hover, setHover] = useState<number | null>(null)
  const pick = hover ?? held
  const [barHover, setBarHover] = useState<string | null>(null)
  const [barOpen, setBarOpen] = useState<string | null>(null)
  const openBar = barHover ?? barOpen

  const shown = useMemo(() => {
    const vis = d.rows.filter(r => r.kind !== 'cmp' || r.sets.some(s => sets.includes(s)))
    const v = (r: Row) => (pick === null ? r.val[year] ?? 0
      : r.seg.filter(s => s.g === pick && (year === 'all' || s.y === year)).reduce((a, s) => a + s.v, 0))
    const main = vis.filter(r => r.kind !== 'mt').sort((a, b) => v(b) - v(a) || a.name.localeCompare(b.name))
    return { won: main.filter(r => v(r) > 0 || r.kind === 'lun'), none: main.filter(r => !(v(r) > 0) && r.kind !== 'lun'),
      mt: vis.filter(r => r.kind === 'mt'), v }
  }, [d.rows, sets, year, pick])
  const max = Math.max(1, ...shown.won.map(r => r.val[year] ?? 0))
  const segs = (r: Row) => r.seg.filter(s => year === 'all' || s.y === year)
  const label = (r: Row) => {
    if (pick === null) return r.tot[year] || d.text.none
    return r.pick.find(p => p.g === pick)?.t[year] ?? '—'
  }
  const toggle = (k: string) => setSets(s => (s.includes(k) ? s.filter(x => x !== k) : [...s, k]))

  const breakdown = (r: Row) => {
    const items = r.pick.filter(p => p.t[year]).sort((a, b) => (b.v[year] ?? 0) - (a.v[year] ?? 0))
    if (!items.length) return null
    return (
      <div role="tooltip" className="absolute left-0 right-0 sm:left-auto sm:w-[340px] z-20 mt-1 px-2.5 py-2 rounded text-[12.5px] leading-snug shadow"
        style={{ top: '100%', background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)' }}>
        <p className="font-semibold mb-1">{r.name}</p>
        <ul className="space-y-0.5">
          {items.map(p => (
            <li key={p.g} className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: tone(p.g), opacity: shade(p.g) }} />
              <span className="min-w-0 flex-1">{d.grants[p.g].name}</span>
              <span className="tabular-nums shrink-0">{p.t[year]}</span>
            </li>))}
        </ul>
        <p className="flex justify-between gap-2 mt-1 pt-1 border-t font-semibold tabular-nums" style={{ borderColor: 'var(--grid)' }}>
          <span>{d.text.total}</span><span>{r.tot[year]}</span></p>
      </div>
    )
  }

  const bar = (r: Row) => (
    <div key={r.name} className="min-w-0 relative cursor-pointer"
      onMouseEnter={() => setBarHover(r.name)} onMouseLeave={() => setBarHover(null)}
      onClick={() => setBarOpen(o => (o === r.name ? null : r.name))}>
      <div className="flex items-baseline justify-between gap-3 text-[13px] leading-tight">
        <span className="min-w-0 truncate" style={{ color: r.kind === 'lun' ? 'var(--thread-2)' : 'var(--text-primary)',
          fontWeight: r.kind === 'lun' ? 700 : 400, fontStyle: r.kind === 'mt' ? 'italic' : undefined }}>
          {r.name}{r.kind === 'mt' ? <span style={{ color: 'var(--text-muted)' }}> · {d.text.mt}</span> : null}</span>
        <span className="tabular-nums shrink-0" style={{ color: 'var(--text-secondary)', fontWeight: r.kind === 'lun' ? 700 : 400 }}>
          {label(r)}</span>
      </div>
      <div className="flex h-[14px] mt-1 rounded-sm overflow-hidden"
        style={{ background: r.kind === 'lun' ? 'color-mix(in srgb, var(--thread-2) 8%, transparent)' : undefined,
          outline: r.kind === 'lun' ? '1px solid color-mix(in srgb, var(--thread-2) 45%, transparent)' : undefined }}>
        {segs(r).map((s, i) => (
          <span key={i} title={`${d.grants[s.g].name}`}
            style={{ width: `${(100 * s.v) / max}%`, background: tone(s.g),
              opacity: pick === null ? shade(s.g) : s.g === pick ? 1 : 0.12,
              borderRight: '1px solid var(--surface-1)', transition: 'opacity 120ms' }} />))}
      </div>
      {r.joint ? <p className="text-[11.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{r.joint}</p> : null}
      {openBar === r.name ? breakdown(r) : null}
    </div>
  )

  return (
    <figure aria-label={alt} className="max-w-3xl min-w-0">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
        <span className="text-[11.5px] uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>{d.text.sets}</span>
        {d.sets.map(s => <Chip key={s.key} on={sets.includes(s.key)} onClick={() => toggle(s.key)}>{s.label}</Chip>)}
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 mt-2">
        <span className="text-[11.5px] uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>{d.text.year}</span>
        {d.years.map(y => <Chip key={y.key} on={year === y.key} onClick={() => setYear(y.key)}>{y.label}</Chip>)}
      </div>

      <p className="text-[12px] mt-3" style={{ color: 'var(--text-muted)' }}>{d.text.bars}</p>

      <div className="mt-4 space-y-2.5">
        {shown.won.map(bar)}
      </div>
      {shown.none.length ? (
        <p className="text-[12.5px] mt-3 pt-2 border-t" style={{ color: 'var(--text-muted)', borderColor: 'var(--grid)' }}>
          <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>{pick === null ? d.text.none : `${d.text.none_pick}: ${d.grants[pick].name}`}</span>
          {' · '}{shown.none.map(r => r.name).join(', ')}</p>) : null}
      {shown.mt.length ? <div className="mt-3">{shown.mt.map(bar)}</div> : null}
      <p className="text-[12px] mt-4 pt-3 border-t" style={{ color: 'var(--text-muted)', borderColor: 'var(--grid)' }}>{d.text.grants}</p>
      <ul className="flex flex-wrap gap-x-1 gap-y-1 mt-1 text-[12px]" onMouseLeave={() => setHover(null)}>
        {d.grants.map((g, i) => (
          <li key={g.name}>
            <button type="button" aria-pressed={held === i}
              onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              onClick={() => { setHover(null); setHeld(h => (h === i ? null : i)) }}
              className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded"
              style={{ color: pick === null || pick === i ? 'var(--text-secondary)' : 'var(--text-muted)',
                background: held === i ? 'var(--surface-2)' : 'transparent', fontWeight: held === i ? 600 : 400,
                opacity: pick === null || pick === i ? 1 : 0.55 }}>
              <span className="inline-block w-3 h-3 rounded-sm shrink-0" style={{ background: tone(i), opacity: shade(i) }} />
              {g.name}
            </button>
          </li>))}
        {held !== null ? (
          <li><button type="button" onClick={() => setHeld(null)} className="px-1.5 py-0.5 underline"
            style={{ color: 'var(--text-secondary)' }}>{d.text.clear}</button></li>) : null}
      </ul>
      <figcaption className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
