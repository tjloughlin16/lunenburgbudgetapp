import {
  Bar, BarChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /monty-tech. Every series arrives from /data/monty-tech.json, written
 *  by scripts/build_monty_tech.py — nothing here computes a figure and nothing here has
 *  one typed into it (rule 2).
 *
 *  THE ONE THING THESE CHARTS HAVE TO DO THAT MOST DO NOT: draw a series where some
 *  points are established and some are not, without letting the eye read them as one.
 *
 *  Eleven of the twelve annual-report figures for this line carry `check failed` or
 *  `no check` — the extractor's own reconciliation, failing — and CLAUDE.md forbids
 *  aggregating across `status`. Plotting them the same way as the ledger figure would do
 *  exactly that, silently, in the one register a reader cannot audit. So:
 *
 *    * ESTABLISHED points are FILLED and joined by a solid line.
 *    * CANDIDATE points are HOLLOW, and nothing joins them. There is no line, because a
 *      line asserts that the space between two points is knowable, and here it is not.
 *    * The distinction is carried by SHAPE as well as by hue, and it is named in the
 *      legend and again in the table twin's own `status` column. Colour is never the only
 *      carrier of it.
 *
 *  COLOUR. Two colour jobs and they never share a chart.
 *
 *  1. IS THIS FIGURE ESTABLISHED. --series-cost for a figure that is, --text-muted for a
 *     candidate. Muted is right for a candidate: it recedes, which is what an unverified
 *     number should do, and it is not a warning colour — the extract is not accused of
 *     anything, it is unconfirmed.
 *  2. WHICH PART OF THE ASSESSMENT. The categorical --mt-* set, four parts under the
 *     district's own names.
 *
 *  ONE AXIS, ALWAYS. Nothing is dual-axis. Where dollars and a count both matter they are
 *  two panels or two charts; the only thing a second y-scale ever proves is whatever the
 *  scales were chosen to prove.
 *
 *  THE SPAN IS ON EVERY CHART, in its own caption. Three years is a trend to a board that
 *  will not project two, and the way that stays honest is naming how many years are drawn.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is one they cannot
 *  check. */

export const SOLID = 'var(--series-cost)'
export const SOFT = 'var(--text-muted)'
export const MINIMUM = 'var(--mt-minimum)'
export const TRANSPORT = 'var(--mt-transport)'
export const CAPITAL = 'var(--mt-capital)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const money = (n: number) => usd(Math.round(n))
export const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
export const pct2 = (x: number) => `${(x * 100).toFixed(2)}%`
export const signedPct = (x: number) =>
  `${x < 0 ? '−' : '+'}${(Math.abs(x) * 100).toFixed(1)}%`

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${Math.round(n)}`

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 200 }}>{children}</div>
  )
}

/** A scrolling table twin. Wide content scrolls inside its own box; the page body never
 *  scrolls sideways. */
export function TableTwin({ head, rows, caption, note, mark }: {
  head: string[]; rows: (string | number)[][]; caption?: string
  note?: React.ReactNode; mark?: (row: (string | number)[]) => boolean
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
            <tr>{head.map((hd, i) => (
              <th key={hd} className="font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
                style={{
                  color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right',
                }}>{hd}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const strong = mark ? mark(r) : false
              return (
                <tr key={i}>
                  {r.map((c, j) => (
                    <td key={j} className="py-1 pr-4 whitespace-nowrap border-b"
                      style={{
                        borderColor: 'var(--grid)',
                        fontWeight: strong ? 700 : 400,
                        color: strong ? 'var(--text-primary)'
                          : j === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                        textAlign: j === 0 ? 'left' : 'right',
                      }}>{c}</td>
                  ))}
                </tr>
              )
            })}
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

export function Legend({ items }: { items: { hue: string; label: string; hollow?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block"
            style={{
              width: 12, height: 12, borderRadius: i.hollow ? 999 : 2,
              background: i.hollow ? 'transparent' : i.hue,
              border: i.hollow ? `2px solid ${i.hue}` : 'none',
            }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}

/** The span, stated on the chart. */
export function Span({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-widest mt-3"
      style={{ color: 'var(--text-muted)' }}>{children}</p>
  )
}

/* ------------------------------------------------- 1. the assessment, and what is known */

export type SeriesRow = {
  fy: number
  required: number | null          // derived from DESE. Established.
  documented: number | null        // stated by the district or the Town's own books.
  candidate: number | null         // off a check-failed annual-report extract.
  ledger: number | null            // out of the accounting system.
  status: string
}

/** THE PAGE'S CENTRAL CHART, and the whole difficulty of this subject in one frame.
 *
 *  The solid line is the state-required minimum, derived from DESE's own workbook for
 *  every year — the one continuous, established series that exists. Everything above it
 *  is what the town was actually billed, and that is where the record gets patchy: four
 *  years the district or the Town states outright (filled), eleven the annual town
 *  reports give and cannot vouch for (hollow, unjoined).
 *
 *  NOT drawn from zero. It is a level and the finding is the GAP between two levels; a
 *  0-based axis would compress twenty years of divergence into a thin band. The table
 *  twin carries every value, which is the relief that licenses it. */
export function AssessmentSeries({ rows }: { rows: SeriesRow[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={44} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={56} tickFormatter={compact}
              domain={['auto', 'auto']} />
            <Tooltip content={({ active, payload }) => {
              const p = payload?.[0]?.payload as SeriesRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  {p.required !== null && (
                    <div>State minimum {money(p.required)}</div>
                  )}
                  {p.ledger !== null && (
                    <div className="font-semibold">Ledger {money(p.ledger)}</div>
                  )}
                  {p.documented !== null && p.ledger === null && (
                    <div className="font-semibold">Assessed {money(p.documented)}</div>
                  )}
                  {p.candidate !== null && (
                    <div style={{ color: 'var(--text-muted)' }}>
                      Annual report {money(p.candidate)} — {p.status}
                    </div>
                  )}
                </Box>
              )
            }} />
            <Line dataKey="required" stroke={SOLID} strokeWidth={2.5} dot={false}
              connectNulls isAnimationActive={false} />
            <Scatter dataKey="documented" fill={SOLID} shape="circle"
              isAnimationActive={false} />
            <Scatter dataKey="ledger" fill={SOLID} shape="diamond"
              isAnimationActive={false} />
            <Scatter dataKey="candidate" fill="none" stroke={SOFT} strokeWidth={2}
              shape="circle" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: SOLID, label: 'the state-required minimum, derived from DESE’s workbook' },
        { hue: SOLID, label: 'what the town was billed — stated by the district or its own books' },
        { hue: SOFT, label: 'the annual town reports — every one fails its own reconciliation', hollow: true },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------- 2. the four parts of the bill */

export type PartRow = {
  fy: number; required: number; transport: number; capital: number; total: number
}

/** Stacked, because these ARE parts of one total and they sum to it exactly — the
 *  generator refuses to write if they stop doing so. A grouped bar would hide the one
 *  thing worth seeing, which is how little of the bar is anything but the first segment.
 *
 *  Drawn from zero, because it is a composition of a total and a truncated stack would
 *  misstate every proportion in it. */
export function Parts({ rows }: { rows: PartRow[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)" />
            <YAxis tick={AXIS} stroke="var(--axis)" width={56} tickFormatter={compact} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as PartRow | undefined
                if (!active || !p) return null
                return (
                  <Box>
                    <div className="font-bold mb-1">{fy(p.fy)}</div>
                    <div>Required minimum {money(p.required)}</div>
                    <div>Transport &amp; operating {money(p.transport)}</div>
                    <div>Capital {money(p.capital)}</div>
                    <div className="mt-1 font-semibold">Total {money(p.total)}</div>
                  </Box>
                )
              }} />
            <Bar dataKey="required" stackId="a" fill={MINIMUM} isAnimationActive={false} />
            <Bar dataKey="transport" stackId="a" fill={TRANSPORT}
              isAnimationActive={false} />
            <Bar dataKey="capital" stackId="a" fill={CAPITAL} radius={[4, 4, 0, 0]}
              isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: MINIMUM, label: 'required minimum contribution — set by the state' },
        { hue: TRANSPORT, label: 'transportation & other operating — by enrolment share' },
        { hue: CAPITAL, label: 'capital — by school-attending children, grades 1–12' },
      ]} />
    </div>
  )
}

/* --------------------------------------------- 3. the money share against the head share */

export type ShareRow = {
  fy: number; rlc_share: number; fe_share: number
}

/** Two lines, one axis, both percentages of the same town. The gap between them is the
 *  finding: Monty Tech is a bigger share of the town's foundation BUDGET than of its
 *  foundation ENROLMENT, because the state's vocational rate per pupil is higher.
 *
 *  The categorical pair, not the diverging one — neither share is better or worse, and
 *  neither is a direction. */
export function Shares({ rows }: { rows: ShareRow[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={44} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={44}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
            <Tooltip content={({ active, payload }) => {
              const p = payload?.[0]?.payload as ShareRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>Share of the town’s bill {pct2(p.rlc_share)}</div>
                  <div>Share of the town’s pupils {pct2(p.fe_share)}</div>
                </Box>
              )
            }} />
            <Line dataKey="rlc_share" stroke={MINIMUM} strokeWidth={2.5} dot={false}
              isAnimationActive={false} />
            <Line dataKey="fe_share" stroke={TRANSPORT} strokeWidth={2.5} dot={false}
              strokeDasharray="4 3" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: MINIMUM, label: 'Monty Tech’s share of Lunenburg’s required contribution' },
        { hue: TRANSPORT, label: 'Monty Tech’s share of Lunenburg’s foundation enrolment' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------ 4. where the town's children are */

export type StudentRow = {
  fy: number; monty_tech: number; school_choice: number; charter: number
}

/** Three counts, one axis, drawn from zero because they are counts and the crossing is
 *  the finding: Monty Tech passes school choice and does not come back.
 *
 *  Bars rather than lines, grouped by year. These are three separate programmes and not
 *  three readings of one quantity, and a reader comparing FY2026's three needs them
 *  adjacent rather than traced. */
export function Students({ rows }: { rows: StudentRow[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={44} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={36} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as StudentRow | undefined
                if (!active || !p) return null
                return (
                  <Box>
                    <div className="font-bold mb-1">{fy(p.fy)}</div>
                    <div>Monty Tech {p.monty_tech}</div>
                    <div>School choice {p.school_choice}</div>
                    <div>Charter {p.charter}</div>
                  </Box>
                )
              }} />
            <Bar dataKey="monty_tech" fill={MINIMUM} isAnimationActive={false} />
            <Bar dataKey="school_choice" fill={TRANSPORT} isAnimationActive={false} />
            <Bar dataKey="charter" fill={CAPITAL} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: MINIMUM, label: 'Monty Tech — resident members of a district Lunenburg belongs to' },
        { hue: TRANSPORT, label: 'school choice — a seat another district opened' },
        { hue: CAPITAL, label: 'charter schools' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------- 5. the town's own forecast */

export type ForecastRow = {
  fy: number; projected: number | null; required: number | null; actual: number | null
}

/** What the town thought this line would do, against what it did. One axis, three marks:
 *  the 2.5%-a-year projection as a dashed line, the state minimum as the solid one that
 *  was actually driving it, and the FY2026 outturn as a single filled point.
 *
 *  Muted for the projection, because a forecast is not a measurement and should not be
 *  drawn like one. Nothing here is red: a forecast that missed is not a fault, it is a
 *  line that turned out to be governed by something other than inflation. */
export function Forecast({ rows, rate }: { rows: ForecastRow[]; rate: number }) {
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)" />
            <YAxis tick={AXIS} stroke="var(--axis)" width={56} tickFormatter={compact}
              domain={['auto', 'auto']} />
            <Tooltip content={({ active, payload }) => {
              const p = payload?.[0]?.payload as ForecastRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  {p.projected !== null && <div>Projected {money(p.projected)}</div>}
                  {p.required !== null && <div>State minimum {money(p.required)}</div>}
                  {p.actual !== null && (
                    <div className="font-semibold">Actual {money(p.actual)}</div>
                  )}
                </Box>
              )
            }} />
            <Line dataKey="projected" stroke={SOFT} strokeWidth={2} dot={{ r: 3 }}
              strokeDasharray="5 4" isAnimationActive={false} />
            <Line dataKey="required" stroke={SOLID} strokeWidth={2.5} dot={false}
              isAnimationActive={false} />
            <Scatter dataKey="actual" fill={SOLID} shape="diamond"
              isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: SOFT, label: `the Select Board’s own projection, at ${pct1(rate)} a year` },
        { hue: SOLID, label: 'the state-required minimum, as it actually moved' },
      ]} />
    </div>
  )
}
