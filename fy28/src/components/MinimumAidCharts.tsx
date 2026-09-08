import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /why-we-only-get-minimum-aid. Every series arrives from
 *  /data/minimum-aid.json, written by scripts/build_minimum_aid.py — nothing here computes
 *  a figure and nothing here has one typed into it (rule 2).
 *
 *  COLOUR. Two questions on this page, and they are different questions, so they get
 *  different colour jobs.
 *
 *  1. WHO DECIDED THIS AID DOLLAR — the formula, or the Legislature overriding it. That is
 *     CATEGORICAL: `FORMULA` keeps --series-cost, the hue this site has always used for the
 *     state's half of a school dollar, and `FLOOR` takes --ch70-floor, a hue added for this
 *     page and validated against both series hues in both modes. Neither is "good" or
 *     "bad" and neither is larger by nature.
 *  2. WHICH WAY THE FORMULA MOVED THE TOWN'S REQUIREMENT — off, or on. That is POLARITY,
 *     so it is the site's existing DIVERGING pair, --series-cost against --series-revenue,
 *     with a zero reference line always drawn. Zero is a real value here: most years the
 *     adjustment is one or the other and never both.
 *
 *  THE TWO JOBS NEVER SHARE A CHART, which is why the floor needed a third hue rather than
 *  borrowing --series-revenue: a mark that means "the Legislature's floor" in one frame
 *  must not mean "money added to the town's bill" in the next.
 *
 *  ONE AXIS, ALWAYS. Nothing here is dual-axis. Where dollars and a share both matter they
 *  are two charts, because the only thing a second y-scale ever proves is whatever the
 *  scales were chosen to prove.
 *
 *  RULE 1 IS DRAWN, NOT JUST WRITTEN. Every series on this page is one stage — DESE's
 *  published calculation for the year — and the chart titles say so. The Governor's-stage
 *  figures the town was quoted are in the prose, beside the enacted ones, and are never on
 *  a chart with them.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is a figure they cannot
 *  check. */

export const FORMULA = 'var(--series-cost)'
export const FLOOR = 'var(--ch70-floor)'
export const OFF = 'var(--series-cost)'
export const ON = 'var(--series-revenue)'
export const MUTED = 'var(--text-muted)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const share = (x: number) => `${(x * 100).toFixed(1)}%`
export const money = (n: number) => usd(Math.round(n))
export const signed = (n: number) => (n < 0 ? `−${money(-n)}` : `+${money(n)}`)
export const dollars2 = (n: number) =>
  `${n < 0 ? '−' : ''}$${Math.abs(n).toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${Math.round(n)}`

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 230 }}>{children}</div>
  )
}

/** A scrolling table twin. Wide content scrolls inside its own box; the page body never
 *  scrolls sideways. */
export function TableTwin({ head, rows, caption, note }: {
  head: string[]; rows: (string | number)[][]; caption?: string; note?: React.ReactNode
}) {
  return (
    <div className="mt-3">
      {caption && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>{caption}</p>
      )}
      <div className="overflow-x-auto -mx-1 px-1">
        <table className="text-[12.5px] tnum border-collapse min-w-full">
          <thead>
            <tr>{head.map((h, i) => (
              <th key={h} className="font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
                style={{
                  color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right',
                }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td key={j} className="py-1 pr-4 whitespace-nowrap border-b"
                    style={{
                      borderColor: 'var(--grid)',
                      color: j === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                      textAlign: j === 0 ? 'left' : 'right',
                    }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && (
        <p className="text-[12px] mt-2 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
          {note}
        </p>
      )}
    </div>
  )
}

export function Legend({ items }: { items: { hue: string; label: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: i.hue }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}

/* ------------------------------------------------ 1. the increase, per foundation pupil */

export type YearRow = {
  fy: number; aid: number; change: number | null; per_pupil: number | null
  enrollment: number; foundation_budget: number; foundation_aid: number
  minimum_aid: number; other_increments: number; reduction: number
  required_local_contribution: number; required_share: number | null
  components_sum: number | null; reconciles: boolean | null; target_aid_pct: number
}

/** THE WHOLE ARGUMENT IN ONE MARK: what each year's Chapter 70 increase came to for each
 *  foundation pupil, coloured by which part of the formula produced it.
 *
 *  Per pupil rather than in dollars, because the floor IS a per-pupil rate — drawing the
 *  same series in dollars would hide the thing that makes the last four years identical to
 *  five other districts. A bar and not a line: these are separate years' decisions, not a
 *  quantity flowing through time. */
export function PerPupil({ rows, onFloor }: { rows: YearRow[]; onFloor: number[] }) {
  const data = rows.filter(r => r.per_pupil !== null)
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={40} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54}
              tickFormatter={(v: number) => `$${v}`} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as YearRow | undefined
              if (!active || !p) return null
              const floored = onFloor.includes(p.fy)
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>Chapter 70 aid rose {signed(p.change ?? 0)}</div>
                  <div>{p.enrollment.toLocaleString()} foundation pupils</div>
                  <div className="font-semibold mt-1">{dollars2(p.per_pupil ?? 0)} a pupil</div>
                  <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
                    {floored
                      ? 'The Legislature’s flat floor. Several other districts land on the identical figure.'
                      : 'Produced by the formula, not by the floor.'}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="per_pupil" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map(d => (
                <Cell key={d.fy} fill={onFloor.includes(d.fy) ? FLOOR : FORMULA} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: FORMULA, label: 'produced by the formula' },
        { hue: FLOOR, label: 'the Legislature’s flat per-pupil floor' },
      ]} />
    </div>
  )
}

/* ---------------------------------------------------- 2. the two aid terms, in dollars */

/** The same years in dollars, split into the formula's own term and the floor. Two
 *  segments of one bar, because they add up to the year's increase and a reader should be
 *  able to see that they do — with a 2px gap so the segments never read as one mark.
 *
 *  Years where the two do not account for the whole change are drawn at the size the
 *  components state and named underneath, rather than silently topped up. */
export function AidTerms({ rows }: { rows: YearRow[] }) {
  const data = rows.filter(r => r.change !== null)
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={40} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54} tickFormatter={compact} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as YearRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>Formula (foundation) aid {money(p.foundation_aid)}</div>
                  <div>Minimum aid {money(p.minimum_aid)}</div>
                  {p.other_increments !== 0 && (
                    <div>Other increments {money(p.other_increments)}</div>)}
                  <div className="mt-1">Aid changed by {signed(p.change ?? 0)}</div>
                  {p.reconciles === false && (
                    <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
                      The components do not sum to the change in this year.
                    </div>)}
                </Box>
              )
            }} />
            <Bar dataKey="foundation_aid" stackId="a" fill={FORMULA} isAnimationActive={false} />
            <Bar dataKey="other_increments" stackId="a" fill={MUTED} isAnimationActive={false} />
            <Bar dataKey="minimum_aid" stackId="a" fill={FLOOR} radius={[4, 4, 0, 0]}
              isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: FORMULA, label: 'foundation aid — the formula’s own term' },
        { hue: MUTED, label: 'the other named increments' },
        { hue: FLOOR, label: 'minimum aid — the flat floor' },
      ]} />
    </div>
  )
}

/* ------------------------------- 3. the required share, against every other district */

export type DistRow = {
  fy: number; districts: number; p25: number; median: number; p75: number
  p_max: number; lunenburg: number; lunenburg_rank_of_districts: string
}

/** Lunenburg's required contribution as a share of its foundation budget, drawn inside the
 *  statewide middle half. A line, because this is one quantity moving through time, and the
 *  band is what makes it readable: 60.4% means nothing until you know that half the state's
 *  districts sit between 54.1% and 81.5%.
 *
 *  NOT plotted from zero, and deliberately: this is a bounded share whose whole story is a
 *  16-point fall and a 4-point recovery, and a 0–100 axis would draw both as flat. The
 *  table twin carries every value as a number, which is the relief that licenses it. */
export function RequiredShare({ rows }: { rows: DistRow[] }) {
  const data = rows.map(r => ({ ...r, band: [r.p25, r.p75] as [number, number] }))
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={40} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54} domain={[0.4, 0.9]}
              tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
            <Tooltip content={({ active, payload }) => {
              const p = payload?.[0]?.payload as DistRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>Lunenburg {share(p.lunenburg)}</div>
                  <div>Statewide median {share(p.median)}</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    middle half {share(p.p25)}–{share(p.p75)}
                  </div>
                  <div className="mt-1">Rank {p.lunenburg_rank_of_districts}, highest first</div>
                </Box>
              )
            }} />
            <Area dataKey="band" stroke="none" fill="var(--surface-3)"
              isAnimationActive={false} />
            <Line dataKey="median" stroke={MUTED} strokeWidth={2} dot={false}
              strokeDasharray="4 3" isAnimationActive={false} />
            <Line dataKey="lunenburg" stroke={FORMULA} strokeWidth={2} dot={false}
              isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: FORMULA, label: 'Lunenburg' },
        { hue: MUTED, label: 'statewide median' },
        { hue: 'var(--surface-3)', label: 'the middle half of all districts' },
      ]} />
    </div>
  )
}

/* ------------------------------- 4. what the formula did to the town's own requirement */

export type ContribRow = {
  fy: number; effort_reduction: number; dollar_increment: number
  excess_effort: number; shortfall: number; acceleration: number
  income_effort: number; property_effort: number
  town_foundation_budget: number; town_enrollment: number
  rlc: number; preliminary: number; target: number; combined_effort_yield: number
  equalized_valuation: number; income: number; mrgf: number
  above_target: boolean; target_share: number | null
}

/** DIVERGING, because the quantity is: in twelve years the formula took money OFF the
 *  town's requirement and in four it has added money on. One bar per year, signed, with a
 *  zero reference line always drawn — the years where it did neither are real zeros and are
 *  shown as such rather than omitted.
 *
 *  A stacked or absolute version of this would hide the entire finding, which is a change
 *  of SIGN and not a change of size. */
export function Adjustment({ rows }: { rows: ContribRow[] }) {
  const data = rows.map(r => ({
    ...r, adjustment: r.dollar_increment - r.effort_reduction,
  }))
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={40} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={60} tickFormatter={compact} />
            <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1.5} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as (ContribRow & { adjustment: number }) | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>{p.above_target
                    ? 'Above its target contribution'
                    : 'Below its target contribution'}</div>
                  {p.effort_reduction > 0 && (
                    <div>Effort reduction −{money(p.effort_reduction)}</div>)}
                  {p.dollar_increment > 0 && (
                    <div>Dollar increment +{money(p.dollar_increment)}</div>)}
                  {p.effort_reduction === 0 && p.dollar_increment === 0 && (
                    <div>No adjustment</div>)}
                  <div className="mt-1">Required contribution {money(p.rlc)}</div>
                </Box>
              )
            }} />
            <Bar dataKey="adjustment" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map(d => (
                <Cell key={d.fy} fill={d.adjustment < 0 ? OFF : ON} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OFF, label: 'the formula took effort OFF the requirement' },
        { hue: ON, label: 'the formula added effort ON to it' },
      ]} />
    </div>
  )
}
