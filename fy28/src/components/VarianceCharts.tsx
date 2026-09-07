import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, Legend,
} from 'recharts'
import { usd, usdShort } from '../model/engine'

/** The charts for /budget-vs-actual. Every series arrives from /data/budget-vs-actual.json,
 *  written by scripts/build_variance_charts.py — nothing here computes a figure and
 *  nothing here has one typed into it (rule 2).
 *
 *  COLOUR IS DIVERGING, and the poles are chosen rather than picked: warm (the site's
 *  --series-revenue) for spending ABOVE budget, cool (--series-cost) for spending BELOW
 *  it, and the site's muted ink for the neutral middle. Two cool hues would not read as
 *  opposite. The pair was validated rather than eyeballed — the data-viz validator on
 *  #2a78d6/#eb6834 against the light surface and #3987e5/#d95926 against the dark one
 *  passes all five computable checks, worst adjacent ΔE 24.7 under protanopia.
 *
 *  Where the two series are IDENTITY rather than polarity — budgeted against spent — the
 *  same two hues do categorical duty, which is the one place on this page a colour means
 *  "which column" instead of "which direction". Both charts that do it carry a legend and
 *  a table, so the identity is never colour alone.
 *
 *  Every chart has a table twin underneath it. That is the accessibility floor here and
 *  it is also the house style: a figure a reader cannot copy out of the page is a figure
 *  they cannot check. */

export const OVER = 'var(--series-revenue)'
export const UNDER = 'var(--series-cost)'
export const NEUTRAL = 'var(--text-muted)'

/** A signed percentage, with the sign OUTSIDE the digits and a typographic minus.
 *
 *  A value under a twentieth of a point renders as a bare `0%`: `−0.0%` is a rounding
 *  artefact wearing a direction, and on a page whose whole subject is direction that is
 *  the one thing it must not do. */
export const pct = (x: number) => {
  if (Math.abs(x) < 0.0005) return '0%'
  const d = Math.abs(x) >= 0.1 ? 0 : 1
  return `${x > 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(d)}%`
}
export const fy = (n: number) => `FY${String(n).slice(2)}`

/** The mark for a range that runs past the axis cap. Drawn rather than a glyph so it
 *  takes the row's own colour and cannot be mistaken for text. */
function Chevron({ dir, colour }: { dir: 'left' | 'right'; colour: string }) {
  return (
    <span aria-hidden className="absolute top-1/2 -translate-y-1/2"
      style={{
        [dir]: 0, width: 0, height: 0,
        borderTop: '5px solid transparent', borderBottom: '5px solid transparent',
        [dir === 'left' ? 'borderRight' : 'borderLeft']: `6px solid ${colour}`,
        opacity: 0.8,
      } as React.CSSProperties} />
  )
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="card p-4">{children}</div>
}

function Chip({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ background: color }} />
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ by year */

export type YearRow = {
  fy: number; lines: number; budgeted: number; spent: number; net: number; pct: number
}

function YearTip({ active, payload }: { active?: boolean; payload?: { payload: YearRow }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {fy(d.fy)} &middot; {d.lines} lines
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Budgeted</span>
        <span className="tnum font-semibold">{usd(d.budgeted)}</span>
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Spent</span>
        <span className="tnum font-semibold">{usd(d.spent)}</span>
      </p>
      <p className="flex justify-between gap-4 mt-1 pt-1 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <span style={{ color: d.net >= 0 ? OVER : UNDER }}>
          {d.net >= 0 ? 'Over budget' : 'Under budget'}
        </span>
        <span className="tnum font-bold" style={{ color: d.net >= 0 ? OVER : UNDER }}>
          {usd(Math.abs(d.net))} &middot; {pct(d.pct)}
        </span>
      </p>
    </div>
  )
}

/** The whole measured budget, year by year, as a distance from its own budget.
 *
 *  A diverging bar rather than two lines: the reader's job is polarity — did the year come
 *  in over or under — and a pair of near-identical multi-million-dollar lines makes a
 *  half-percent miss invisible, which is the opposite of the point. */
export function YearVariance({ rows }: { rows: YearRow[] }) {
  /** A symmetric domain rounded UP to a clean half-point, so the axis reads
   *  −3%, −1.5%, 0, +1.5%, +3% rather than the arbitrary endpoints a raw 1.25× headroom
   *  produces. The zero tick has to be one of them: it is the baseline every bar is read
   *  against. */
  const span = Math.ceil(Math.max(...rows.map(r => Math.abs(r.pct))) * 1.25 * 200) / 200
  const ticks = [-span, -span / 2, 0, span / 2, span]
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={UNDER}>spent less than budgeted</Chip>
        <Chip color={OVER}>spent more</Chip>
      </div>
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis domain={[-span, span]} ticks={ticks} width={52}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => `${((v as number) * 100).toFixed(1)}%`} />
            <Tooltip content={<YearTip />} cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Bar dataKey="pct" isAnimationActive={false} radius={[4, 4, 0, 0]} maxBarSize={54}>
              {rows.map(r => (
                <Cell key={r.fy} fill={r.pct >= 0 ? OVER : UNDER} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">
          The measured school budget against what was spent, by fiscal year
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Lines</th>
            <th className="font-semibold py-1.5 text-right">Budgeted</th>
            <th className="font-semibold py-1.5 text-right">Spent</th>
            <th className="font-semibold py-1.5 text-right">Difference</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Lines" className="py-1.5 text-right">{r.lines}</td>
              <td data-label="Budgeted" className="py-1.5 text-right">{usd(r.budgeted)}</td>
              <td data-label="Spent" className="py-1.5 text-right">{usd(r.spent)}</td>
              <td data-label="Difference" className="py-1.5 text-right font-semibold"
                style={{ color: r.net >= 0 ? OVER : UNDER }}>
                {usd(r.net)} &middot; {pct(r.pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* --------------------------------------------------------------- the spread */

export type SpreadRow = { bin: string; lo: number; hi: number; count: number; centred: boolean }

function SpreadTip({ active, payload, total }: {
  active?: boolean; payload?: { payload: SpreadRow }[]; total: number
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold" style={{ color: 'var(--text-secondary)' }}>{d.bin}</p>
      <p className="tnum font-bold mt-0.5">
        {d.count} line-years <span className="font-normal"
          style={{ color: 'var(--text-muted)' }}>
          &middot; {((d.count / total) * 100).toFixed(0)}%
        </span>
      </p>
    </div>
  )
}

/** How far a single line missed, counted. The bins are set in the generator, because
 *  where the edges fall is part of the finding rather than a rendering choice. */
export function Spread({ rows }: { rows: SpreadRow[] }) {
  const total = rows.reduce((a, r) => a + r.count, 0)
  const colour = (r: SpreadRow) => (r.centred ? NEUTRAL : r.lo >= 0 ? OVER : UNDER)
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={UNDER}>the line came in under</Chip>
        <Chip color={NEUTRAL}>within 2% either way</Chip>
        <Chip color={OVER}>the line came in over</Chip>
      </div>
      <div style={{ width: '100%', height: 290 }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical"
            margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            {/* Wide enough for the longest bin name at this size. At 104 Recharts
                clipped "25–50% under" to "25–50%", which silently drops the direction —
                the one thing the label is carrying. */}
            <YAxis type="category" dataKey="bin" width={122} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            <Tooltip content={<SpreadTip total={total} />}
              cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            <Bar dataKey="count" isAnimationActive={false} radius={[0, 4, 4, 0]}
              maxBarSize={16}>
              {rows.map(r => <Cell key={r.bin} fill={colour(r)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-3 tnum">
        <caption className="sr-only">
          Every measured line-year, counted by how far the spending landed from that
          line&rsquo;s own budget
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">How far off</th>
            <th className="font-semibold py-1.5 text-right">Line-years</th>
            <th className="font-semibold py-1.5 text-right">Share</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.bin} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{r.bin}</td>
              <td data-label="Line-years" className="py-1.5 text-right">{r.count}</td>
              <td data-label="Share" className="py-1.5 text-right">
                {((r.count / total) * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------ budget against actual, paired */

export type PairRow = {
  fy: number; budgeted: number; spent: number; lines: number; pct: number
}

function PairTip({ active, payload }: { active?: boolean; payload?: { payload: PairRow }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {fy(d.fy)} &middot; {d.lines} {d.lines === 1 ? 'line' : 'lines'}
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: UNDER }}>Budgeted</span>
        <span className="tnum font-semibold">{usd(d.budgeted)}</span>
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: OVER }}>Spent</span>
        <span className="tnum font-semibold">{usd(d.spent)}</span>
      </p>
      <p className="tnum font-bold mt-1 pt-1 border-t" style={{ borderColor: 'var(--grid)' }}>
        {pct(d.pct)}
      </p>
    </div>
  )
}

/** One group of lines, budget beside actual, year by year. Two bars per year rather than
 *  a variance bar: this is the chart where the reader has to see that the SIZE of the
 *  budget moves too, not only the miss. */
export function BudgetVsSpent({ rows, height = 240 }: { rows: PairRow[]; height?: number }) {
  return (
    <Card>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 4, right: 12, bottom: 4, left: 4 }}
            barGap={2}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={54} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip content={<PairTip />} cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            <Legend verticalAlign="top" height={26} iconType="square"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => (v === 'budgeted' ? 'Budgeted' : 'Spent')} />
            <Bar dataKey="budgeted" fill={UNDER} isAnimationActive={false}
              radius={[4, 4, 0, 0]} maxBarSize={26} />
            <Bar dataKey="spent" fill={OVER} isAnimationActive={false}
              radius={[4, 4, 0, 0]} maxBarSize={26} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-3 tnum">
        <caption className="sr-only">Budgeted against spent, by fiscal year</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Budgeted</th>
            <th className="font-semibold py-1.5 text-right">Spent</th>
            <th className="font-semibold py-1.5 text-right">Miss</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Budgeted" className="py-1.5 text-right">{usd(r.budgeted)}</td>
              <td data-label="Spent" className="py-1.5 text-right">{usd(r.spent)}</td>
              <td data-label="Miss" className="py-1.5 text-right font-semibold"
                style={{ color: r.pct >= 0 ? OVER : UNDER }}>{pct(r.pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* --------------------------------------------------------------- group ranges */

export type GroupRow = {
  group: string; years: number; budgeted: number; spent: number; net: number
  gross: number; churn: number | null; worst: number; best: number
  direction: string | null; drift: number | null
  by_year: { fy: number; budgeted: number; spent: number; pct: number }[]
}

/** Worst year to best year for one group, with the pooled result marked on it.
 *
 *  Drawn as a track rather than as a chart library form, because the finding is a RANGE
 *  and every range chart in Recharts is a stacked bar wearing a disguise. The pooled dot
 *  is the whole point: it is what a net figure sees, and the bar behind it is what that
 *  net figure hides.
 *
 *  Rows are ordered by the caller. Colour is by DIRECTION, never by rank, so filtering
 *  the list does not repaint the survivors. */
export function GroupRanges({ rows, span }: { rows: GroupRow[]; span: number }) {
  const at = (x: number) => `${((x + span) / (2 * span)) * 100}%`
  const clamp = (x: number) => Math.max(-span, Math.min(span, x))
  return (
    <div className="card p-4">
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-4">
        <Chip color={UNDER}>under in every measured year</Chip>
        <Chip color={NEUTRAL}>misses both ways</Chip>
        <Chip color={OVER}>over in every measured year</Chip>
      </div>

      {/* The scale, stated once. Without it the tracks are twelve unlabelled sliders:
          a reader can see that one group is wider than another and cannot see how wide
          either of them is. */}
      <div className="relative h-4 text-[10px] tnum select-none"
        style={{ color: 'var(--text-muted)' }}>
        <span className="absolute left-0">{pct(-span)}</span>
        <span className="absolute -translate-x-1/2" style={{ left: at(0) }}>0</span>
        <span className="absolute right-0">{pct(span)}</span>
      </div>

      <ul>
        {rows.map(r => {
          const colour = r.direction === 'under every year' ? UNDER
            : r.direction === 'over every year' ? OVER : NEUTRAL
          const lo = clamp(r.worst), hi = clamp(r.best)
          const pooled = clamp(r.net / r.budgeted)
          return (
            <li key={r.group} className="border-t pt-2.5 pb-3" style={{ borderColor: 'var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[13px] font-semibold leading-tight">{r.group}</span>
                <span className="text-[11.5px] tnum shrink-0"
                  style={{ color: 'var(--text-muted)' }}>
                  {r.years} yrs &middot; {usdShort(r.budgeted)}
                </span>
              </div>
              {/* The whole strip is the hit target — 44px of height including its padding,
                  so a thumb lands on the row rather than on the 7px bar inside it. */}
              <div className="relative h-[26px] my-0.5"
                title={`${r.group}: ${pct(r.worst)} in its worst year, ${pct(r.best)} in its best, `
                  + `${pct(r.net / r.budgeted)} pooled across ${r.years} years`}>
                <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2"
                  style={{ background: 'var(--grid)' }} />
                {/* The zero rule runs the full height of the strip rather than a stub, and
                    it is the only element on the row drawn in the axis colour. Every bar
                    on this list is read against it. */}
                <div className="absolute inset-y-0 w-px"
                  style={{ left: at(0), background: 'var(--axis)' }} />
                <div className="absolute top-1/2 h-[7px] -translate-y-1/2"
                  style={{
                    left: at(lo), width: `${((hi - lo) / (2 * span)) * 100}%`,
                    background: colour, opacity: 0.45, minWidth: 3,
                    borderTopLeftRadius: r.worst < lo ? 0 : 999,
                    borderBottomLeftRadius: r.worst < lo ? 0 : 999,
                    borderTopRightRadius: r.best > hi ? 0 : 999,
                    borderBottomRightRadius: r.best > hi ? 0 : 999,
                  }} />
                {/* A square end where the bar has been cut by the axis cap, and a chevron
                    past it. A rounded end would say the range stops there, which on the
                    one group that runs to −61% would be a drawing that disagrees with the
                    number printed underneath it. */}
                {r.worst < lo && <Chevron dir="left" colour={colour} />}
                {r.best > hi && <Chevron dir="right" colour={colour} />}
                <div className="absolute top-1/2 w-[11px] h-[11px] -translate-y-1/2
                                -translate-x-1/2 rounded-full"
                  style={{ left: at(pooled), background: colour,
                    boxShadow: '0 0 0 2px var(--surface-1)' }} />
              </div>
              <p className="text-[11.5px] tnum" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: UNDER }}>{pct(r.worst)}</span>
                {' to '}
                <span style={{ color: OVER }}>{pct(r.best)}</span>
                {' · pooled '}<strong>{pct(r.net / r.budgeted)}</strong>
                {r.churn !== null && r.churn >= 2
                  && <> · {r.churn.toFixed(1)}&times; churn</>}
              </p>
            </li>
          )
        })}
      </ul>
      <p className="text-[11px] mt-4" style={{ color: 'var(--text-muted)' }}>
        The bar runs from the group&rsquo;s worst measured year to its best. The dot is the
        pooled result across all of them &mdash; what a single net figure would report.
        Churn is gross variance over net; a high number means the years cancel. The axis is
        capped at {pct(span)}, so that one group running to several times that does not
        squash every other group into the middle; a bar that runs past the cap is drawn cut,
        with a chevron, and the figures under it are always the real ones.
      </p>
    </div>
  )
}
