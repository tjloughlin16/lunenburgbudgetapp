/** EVERY RECORDED MOVE, DATED (fy2026-breakdown): one fiscal year, July to June, in three lanes
 *  -- budget transfers between lines, cost moved between funds by journal entry, and money that
 *  crossed from one year to another (orders carried in; next year's bills paid early).
 *
 *  Each mark is one journal, its height its size on one scale for every lane, so a June cluster
 *  reads as a June cluster. Hover or tap a mark for the Town's own memo and what moved where.
 *  Under the lanes, every entry as a list, in date order or largest first.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Ev = { lane: string; day: number; date: string; value: number; text: string; title: string; detail: string }
type Year = { fy: string; events: Ev[]; months: string[] }
type Data = { years: Year[]; lanes: { id: string; label: string }[]
  text: { list: string; biggest: string; order: string; none: string } }

const W = 720, LANE = 70, PAD = 14
const COLOR: Record<string, string> = { transfer: 'var(--thread-1)', moved: 'var(--thread-2)', year: 'var(--thread-4)' }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

export default function FyMovesTimeline({ data, alt }: CustomProps) {
  const d = data as Data
  const [yi, setYi] = useState(d.years.length - 1)
  const [hot, setHot] = useState<number | null>(null)
  const [held, setHeld] = useState<number | null>(null)
  const [big, setBig] = useState(false)
  const y = d.years[yi]
  const tip = hot ?? held
  const max = Math.max(1, ...d.years.flatMap(v => v.events.map(e => e.value)))
  const H = d.lanes.length * LANE + 22
  const x = (day: number) => PAD + (day / 365) * (W - 2 * PAD)
  const list = useMemo(() => y.events.map((e, i) => ({ e, i })).sort((a, b) => (big ? b.e.value - a.e.value : 0)), [y, big])

  return (
    <figure aria-label={alt} className="max-w-3xl">
      <div className="flex flex-wrap gap-1.5">
        {d.years.map((v, i) => <Chip key={v.fy} on={i === yi} onClick={() => { setYi(i); setHeld(null) }}>{v.fy}</Chip>)}
      </div>
      <div className="relative mt-3">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block" role="img" aria-label={alt} onMouseLeave={() => setHot(null)}>
          {d.lanes.map((l, li) => (
            <g key={l.id}>
              <line x1={PAD} x2={W - PAD} y1={(li + 1) * LANE} y2={(li + 1) * LANE} stroke="var(--grid)" />
              <text x={PAD} y={li * LANE + 13} fontSize={12} fill="var(--text-secondary)">{l.label}</text>
            </g>))}
          {y.months.map((m, i) => (
            <text key={m} x={x(i * 30.4 + 15)} y={H - 6} fontSize={11} textAnchor="middle" fill="var(--text-muted)">{m}</text>))}
          {y.events.map((e, i) => {
            const li = d.lanes.findIndex(l => l.id === e.lane)
            const h = Math.max(2, (e.value / max) * (LANE - 22))
            const on = tip === null || tip === i
            return (
              <rect key={i} x={x(e.day) - 2.5} y={(li + 1) * LANE - h} width={5} height={h} rx={1}
                fill={COLOR[e.lane]} opacity={on ? 0.9 : 0.2} style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHot(i)} onClick={() => setHeld(v => (v === i ? null : i))}>
                <title>{`${e.date} · ${e.title}: ${e.text}`}</title>
              </rect>)
          })}
        </svg>
        {tip !== null && y.events[tip] ? (
          <div role="status" className="mt-2 sm:absolute sm:right-0 sm:top-0 sm:w-[320px] px-2.5 py-2 rounded text-[12.5px] leading-snug shadow"
            style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
            <p className="font-semibold">{y.events[tip].date} · {y.events[tip].title}</p>
            <p className="tabular-nums mt-0.5">{y.events[tip].text}</p>
            {y.events[tip].detail ? <p className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>{y.events[tip].detail}</p> : null}
          </div>) : null}
      </div>
      <details className="mt-3">
        <summary className="cursor-pointer text-[13.5px] font-semibold">{d.text.list}</summary>
        <div className="flex gap-1.5 mt-2">
          <Chip on={!big} onClick={() => setBig(false)}>{d.text.order}</Chip>
          <Chip on={big} onClick={() => setBig(true)}>{d.text.biggest}</Chip>
        </div>
        <ul className="mt-2 text-[13px] divide-y" style={{ borderColor: 'var(--grid)' }}>
          {list.map(({ e, i }) => (
            <li key={i} className="py-1.5 grid grid-cols-[auto_1fr_auto] gap-x-3 items-baseline" style={{ borderColor: 'var(--grid)' }}>
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR[e.lane] }} />
              <span className="min-w-0"><span style={{ color: 'var(--text-muted)' }}>{e.date}</span> · {e.title}
                {e.detail ? <span className="block text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>{e.detail}</span> : null}</span>
              <span className="tabular-nums text-right">{e.text}</span>
            </li>))}
        </ul>
      </details>
    </figure>
  )
}
