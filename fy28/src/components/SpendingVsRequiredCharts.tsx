import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /what-the-state-requires-us-to-spend. Every series arrives from
 *  /data/spending-vs-required.json, written by scripts/build_spending_vs_required.py —
 *  nothing here computes a headline and nothing here has a figure typed into it (rule 2).
 *
 *  RULE 1 IS DRAWN, NOT ONLY WRITTEN, AND IT IS THE WHOLE DESIGN OF THIS FILE.
 *  `nss_stage` is ACTUAL for the long series and BUDGETED for the last two years. Those
 *  are two stages of one quantity. So every chart here splits the years into two SEPARATE
 *  dataKeys — `*_actual` and `*_budgeted` — holding `null` outside their own stage. Two
 *  keys cannot produce one path, which is the point: a reader cannot be shown a trend
 *  through a change of instrument even by accident, and neither can a future edit
 *  accidentally reintroduce one by changing a prop.
 *
 *  The budgeted marks are also drawn DIFFERENTLY — dashed stroke, hollow dots — because
 *  the separation has to survive a reader who does not read the caption. Form carries the
 *  stage; colour carries the series. Those two jobs never swap.
 *
 *  COLOUR. One job only: WHICH SERIES. `OURS` is Lunenburg, `FIELD` is the state — the
 *  same assignment /what-other-districts-spend uses, because a reader arriving from that
 *  page must not have to relearn what blue means. Nothing here is coloured good or bad.
 *  Spending further below the median is drawn in the same hue as spending above it, and
 *  the relief is position on an axis.
 *
 *  ONE AXIS, ALWAYS. Ratios and dollars are different charts, never a second y-scale.
 *
 *  THE SPAN IS ON EVERY CHART, in its caption. TJ's rule: three years is a trend in this
 *  town, and the way that stays honest is saying how many years are drawn — which cuts
 *  the other way here, where thirty-one is far more than anything else on this site and
 *  the reader should be told that too.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is one they cannot
 *  check. */

export const OURS = 'var(--series-cost)'
export const FIELD = 'var(--text-muted)'
export const BAND = 'var(--surface-3)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const fyLong = (n: number) => `FY${n}`
export const money = (n: number) => usd(Math.round(n))
export const signedUsd = (n: number) =>
  (n < 0 ? `−${money(-n)}` : n > 0 ? `+${money(n)}` : money(0))
export const ratio = (x: number) => x.toFixed(4)
export const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${Math.round(n)}`

/** One year of DESE's net school spending comparison, at one stage. */
export type Year = {
  fy: number
  required: number
  spent: number
  ratio: number
  above_required: number
  state_median: number | null
  p25: number | null
  p75: number | null
  rank: number | null
  districts: number | null
  at_state_median: number | null
  short_of_median: number | null
}

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 240 }}>{children}</div>
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

export function Legend({ items }: { items: { hue: string; label: string; dashed?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          {i.dashed
            ? <span className="inline-block" style={{
              width: 14, height: 0, borderTop: `2px dashed ${i.hue}`,
            }} />
            : <span className="inline-block rounded-[2px]"
              style={{ width: 12, height: 12, background: i.hue }} />}
          {i.label}
        </span>
      ))}
    </div>
  )
}

/** The two stages, merged onto one x-axis and into FOUR keys that can never join up.
 *
 *  This is the only place the two arrays meet, and they meet as separate columns of one
 *  row set. Nothing downstream can difference them, because no row ever carries both. */
function stack(actual: Year[], budgeted: Year[]) {
  const rows = [
    ...actual.map(r => ({ ...r, stage: 'actual' as const })),
    ...budgeted.map(r => ({ ...r, stage: 'budgeted' as const })),
  ].sort((a, b) => a.fy - b.fy)
  return rows.map(r => ({
    ...r,
    ours_actual: r.stage === 'actual' ? r.ratio : null,
    ours_budgeted: r.stage === 'budgeted' ? r.ratio : null,
    median_actual: r.stage === 'actual' ? r.state_median : null,
    median_budgeted: r.stage === 'budgeted' ? r.state_median : null,
    rank_actual: r.stage === 'actual' ? r.rank : null,
    rank_budgeted: r.stage === 'budgeted' ? r.rank : null,
    half: r.districts ? r.districts / 2 : null,
    band_lo: r.stage === 'actual' ? r.p25 : null,
    band_hi: r.stage === 'actual' && r.p25 !== null && r.p75 !== null
      ? r.p75 - r.p25 : null,
  }))
}

function StageTip({ p }: { p: ReturnType<typeof stack>[number] }) {
  return (
    <Box>
      <div className="font-bold mb-1">{fyLong(p.fy)}</div>
      <div>Lunenburg spent {money(p.spent)}</div>
      <div>the minimum required was {money(p.required)}</div>
      <div className="font-semibold mt-1">
        {ratio(p.ratio)} times the requirement
      </div>
      {p.state_median !== null && (
        <div>the median district: {ratio(p.state_median)}</div>
      )}
      {p.rank !== null && p.districts !== null && (
        <div className="mt-1">rank {p.rank} of {p.districts}, highest first</div>
      )}
      <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
        {p.stage === 'actual'
          ? 'Actual net school spending, as DESE later reported it.'
          : 'BUDGETED net school spending. A different stage of the same quantity — never differenced against the actual years.'}
      </div>
    </Box>
  )
}

/* ------------------------------------------------------------------ 1. where we RANK */

/** THE CHART THAT CARRIES THE ARGUMENT: position among every district in the state, in
 *  the same year, under the same formula.
 *
 *  Rank rather than ratio, because the ratio moves when the REQUIREMENT moves and the
 *  requirement is recomputed every year from enrolment and municipal wealth. A rank asks
 *  a question the requirement cannot contaminate: of the districts all facing this year's
 *  formula, how many spent a larger multiple of their own minimum.
 *
 *  The axis is REVERSED so that first place is at the top, which is the only orientation
 *  a reader does not have to be told about. The field is drawn behind it as a band from
 *  first to last place, and the halfway mark as a line, so a rank is legible without
 *  knowing how many districts there were that year — which changes. */
export function Rank({ actual, budgeted }: { actual: Year[]; budgeted: Year[] }) {
  const data = stack(actual, budgeted).filter(r => r.rank !== null)
  const worst = Math.max(...data.map(r => r.districts ?? 0))
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={2} angle={-45} textAnchor="end" height={42} />
            <YAxis reversed domain={[1, worst]} tick={AXIS} stroke="var(--axis)" width={44}
              tickFormatter={(v: number) => String(Math.round(v))} />
            <Tooltip cursor={{ stroke: 'var(--axis)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as ReturnType<typeof stack>[number] | undefined
              return active && p ? <StageTip p={p} /> : null
            }} />
            <Line type="monotone" dataKey="half" stroke={FIELD} strokeWidth={1}
              strokeDasharray="1 4" dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="rank_actual" stroke={OURS} strokeWidth={2}
              dot={{ r: 1.8, fill: OURS, strokeWidth: 0 }} isAnimationActive={false}
              connectNulls={false} />
            <Line type="monotone" dataKey="rank_budgeted" stroke={OURS} strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3.4, fill: 'var(--surface-1)', stroke: OURS, strokeWidth: 1.6 }}
              isAnimationActive={false} connectNulls={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg’s rank — actual spending' },
        { hue: OURS, label: 'the same rank on BUDGETED spending, a different stage', dashed: true },
        { hue: FIELD, label: 'the middle of the field that year', dashed: true },
      ]} />
    </div>
  )
}

/* ------------------------------------------------- 2. the ratio, against the state's */

/** The same years as a ratio, with the state's middle half behind it.
 *
 *  Second and not first, because this is the series a reader will over-read: a line that
 *  climbs looks like effort rising, and every district's line climbs. The band is what
 *  stops that — it is the 25th to the 75th percentile of every district in the same year,
 *  so a reader can see the whole field moving under the line. */
export function Ratio({ actual, budgeted }: { actual: Year[]; budgeted: Year[] }) {
  const data = stack(actual, budgeted)
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={2} angle={-45} textAnchor="end" height={42} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={44}
              tickFormatter={(v: number) => v.toFixed(1)} />
            <ReferenceLine y={1} stroke="var(--axis)" strokeWidth={1.5} />
            <Tooltip cursor={{ stroke: 'var(--axis)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as ReturnType<typeof stack>[number] | undefined
              return active && p ? <StageTip p={p} /> : null
            }} />
            <Area dataKey="band_lo" stackId="band" stroke="none" fill="transparent"
              isAnimationActive={false} />
            <Area dataKey="band_hi" stackId="band" stroke="none" fill={BAND}
              isAnimationActive={false} />
            <Line type="monotone" dataKey="median_actual" stroke={FIELD} strokeWidth={1.6}
              dot={false} isAnimationActive={false} connectNulls={false} />
            <Line type="monotone" dataKey="median_budgeted" stroke={FIELD} strokeWidth={1.6}
              strokeDasharray="5 4" dot={false} isAnimationActive={false}
              connectNulls={false} />
            <Line type="monotone" dataKey="ours_actual" stroke={OURS} strokeWidth={2}
              dot={{ r: 1.8, fill: OURS, strokeWidth: 0 }} isAnimationActive={false}
              connectNulls={false} />
            <Line type="monotone" dataKey="ours_budgeted" stroke={OURS} strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3.4, fill: 'var(--surface-1)', stroke: OURS, strokeWidth: 1.6 }}
              isAnimationActive={false} connectNulls={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg, actual spending over its own requirement' },
        { hue: OURS, label: 'Lunenburg, BUDGETED — a different stage', dashed: true },
        { hue: FIELD, label: 'the median district, same measure' },
        { hue: BAND, label: 'the middle half of every district in the state' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------ 3. the counterfactual */

/** WHAT THE GAP IS WORTH IN DOLLARS, and it is arithmetic and not a proposal.
 *
 *  Each bar is the year's required minimum multiplied by the state's median ratio, less
 *  what Lunenburg actually spent. Above the line means the town spent less than a median
 *  district would have on the same requirement; below it means more. Nobody has proposed
 *  any of these amounts and nothing here says what they would buy.
 *
 *  One hue, signed, with zero always drawn. A diverging pair would put a colour on
 *  "spending less", and this page is not a scorecard. */
export function Counterfactual({ actual }: { actual: Year[] }) {
  const data = actual.filter(r => r.short_of_median !== null)
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={2} angle={-45} textAnchor="end" height={42} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={56} tickFormatter={compact} />
            <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1.5} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as Year | undefined
                if (!active || !p) return null
                const short = p.short_of_median ?? 0
                return (
                  <Box>
                    <div className="font-bold mb-1">{fyLong(p.fy)}</div>
                    <div>spent {money(p.spent)}</div>
                    <div>at the median ratio: {money(p.at_state_median ?? 0)}</div>
                    <div className="font-semibold mt-1">
                      {short > 0 ? `${money(short)} less` : `${money(-short)} more`} than a
                      median district on the same requirement
                    </div>
                    <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
                      Arithmetic on a published median. Not a costed programme, and nobody
                      proposed it.
                    </div>
                  </Box>
                )
              }} />
            <Bar dataKey="short_of_median" fill={OURS} radius={[2, 2, 0, 0]}
              isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'above the line: less than a median district would have spent' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------ 4. the two sides, in dollars */

/** What was required and what was spent, both in dollars, actual years only.
 *
 *  The ratio charts answer "how far above", and this one answers the question they hide:
 *  how much of the movement is the town and how much is the requirement. Both lines are
 *  the same stage and the same table, so they may be read against each other. */
export function Dollars({ actual }: { actual: Year[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={actual} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={2} angle={-45} textAnchor="end" height={42} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={56} tickFormatter={compact} />
            <Tooltip cursor={{ stroke: 'var(--axis)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as Year | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fyLong(p.fy)}</div>
                  <div>required minimum {money(p.required)}</div>
                  <div>net school spending {money(p.spent)}</div>
                  <div className="font-semibold mt-1">
                    {money(p.above_required)} above the floor
                  </div>
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="spent" stroke={OURS} strokeWidth={2} dot={false}
              isAnimationActive={false} />
            <Line type="monotone" dataKey="required" stroke={FIELD} strokeWidth={1.6}
              dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'net school spending, as reported' },
        { hue: FIELD, label: 'the minimum Chapter 70 required that year' },
      ]} />
    </div>
  )
}
