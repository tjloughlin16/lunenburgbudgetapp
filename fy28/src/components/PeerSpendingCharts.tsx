import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /what-other-districts-spend. Every series arrives from
 *  /data/peer-spending.json, written by scripts/build_peer_spending.py — nothing here
 *  computes a figure and nothing here has one typed into it (rule 2).
 *
 *  COLOUR. Two colour jobs on this page and they never share a chart.
 *
 *  1. WHICH DISTRICT IS OURS. Lunenburg takes --series-cost; every other district takes
 *     --text-muted, undifferentiated on purpose. Six hues would say "here are six
 *     districts ranked", and the page's own argument is that the six-district set is OURS
 *     and carries no claim on its own. One town against a field is what is being drawn.
 *  2. MONEY AGAINST PUPILS. The decomposition chart draws two quantities that are neither
 *     opposite nor ordered, so it is the CATEGORICAL pair --pp-money / --pp-pupils, and
 *     never the diverging --series-cost/--series-revenue: on this page --series-cost
 *     already means "our town".
 *
 *  NOT A SCORECARD, AND THE MARKS SAY SO. No hue here means good or bad. Spending less is
 *  drawn in the same colour as spending more, and where a value is below a comparison the
 *  relief is position on an axis, never a red.
 *
 *  ONE AXIS, ALWAYS. Nothing is dual-axis. Where dollars and a count both matter they are
 *  two panels of one chart, because the only thing a second y-scale ever proves is
 *  whatever the scales were chosen to prove.
 *
 *  THE SPAN IS ON EVERY CHART, in its own caption — TJ's rule: three years is a trend in
 *  this town, and the way that stays honest is saying how many years are drawn.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is a figure they
 *  cannot check. */

export const OURS = 'var(--series-cost)'
export const FIELD = 'var(--text-muted)'
export const MONEY = 'var(--pp-money)'
export const PUPILS = 'var(--pp-pupils)'
export const BAND = 'var(--surface-3)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const money = (n: number) => usd(Math.round(n))
export const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
export const signedPct = (x: number) =>
  `${x < 0 ? '−' : '+'}${(Math.abs(x) * 100).toFixed(1)}%`
export const signedUsd = (n: number) =>
  (n < 0 ? `−${money(-n)}` : n > 0 ? `+${money(n)}` : money(0))

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${Math.round(n)}`

/** Names are long and the axis is not. Shortened for the tick only; every table twin and
 *  every tooltip carries the district's full name. */
export const shortName = (d: string) => d
  .replace(' School District', '')
  .replace('Ashburnham-Westminster', 'Ashburnham-West.')
  .replace('ASHBURNHAM WESTMINSTER', 'Ashburnham-West.')
  .replace('GROTON DUNSTABLE', 'Groton-Dunstable')
  .replace('NORTH MIDDLESEX', 'North Middlesex')
  .replace('AYER SHIRLEY', 'Ayer Shirley')
  .replace('LUNENBURG', 'Lunenburg')
  .replace('HARVARD', 'Harvard')

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 220 }}>{children}</div>
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
            <tr>{head.map((h, i) => (
              <th key={h} className="font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
                style={{
                  color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right',
                }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const ours = mark ? mark(r) : false
              return (
                <tr key={i}>
                  {r.map((c, j) => (
                    <td key={j} className="py-1 pr-4 whitespace-nowrap border-b"
                      style={{
                        borderColor: 'var(--grid)',
                        fontWeight: ours ? 700 : 400,
                        color: ours ? 'var(--text-primary)'
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

/** The span, stated on the chart. Three years is a trend to a board that will not project
 *  two, and the way that stays honest is naming how many years are drawn. */
export function Span({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-widest mt-3"
      style={{ color: 'var(--text-muted)' }}>{children}</p>
  )
}

/* --------------------------------------- 1. Lunenburg inside the statewide distribution */

export type SwRow = {
  fy: number; districts: number; p25: number; median: number; p75: number
  p_min: number; p_max: number; lunenburg: number; rank: number
  spend_less: number; percentile: number; below_median: number
  in_bottom_quarter: boolean
}

/** THE HEADLINE, and the reason it is the headline: Lunenburg against every district in
 *  Massachusetts rather than against five we picked.
 *
 *  The band is the middle half of the state, the dashed line the median, and the solid
 *  line the town. A line rather than bars because this is one quantity moving through
 *  time; the band is what makes the level readable at all, since $18,027 means nothing
 *  until you know the middle half of the state is $21,179 to $26,961.
 *
 *  NOT drawn from zero. It is a level, not a total, and the whole finding is a position
 *  inside a distribution — a 0-based axis would draw the band and the town as one thick
 *  stripe. The table twin carries every value, which is the relief that licenses it. */
export function Statewide({ rows }: { rows: SwRow[] }) {
  const data = rows.map(r => ({ ...r, band: [r.p25, r.p75] as [number, number] }))
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={AXIS} stroke="var(--axis)"
              interval={0} angle={-45} textAnchor="end" height={40} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54} tickFormatter={compact} />
            <Tooltip content={({ active, payload }) => {
              const p = payload?.[0]?.payload as SwRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{fy(p.fy)}</div>
                  <div>Lunenburg {money(p.lunenburg)}</div>
                  <div>Statewide median {money(p.median)}</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    middle half {money(p.p25)}–{money(p.p75)}
                  </div>
                  <div className="mt-1">
                    Rank {p.rank} of {p.districts} — {p.spend_less} spend less
                  </div>
                </Box>
              )
            }} />
            <Area dataKey="band" stroke="none" fill={BAND} isAnimationActive={false} />
            <Line dataKey="median" stroke={FIELD} strokeWidth={2} dot={false}
              strokeDasharray="4 3" isAnimationActive={false} />
            <Line dataKey="lunenburg" stroke={OURS} strokeWidth={2.5} dot={false}
              isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg' },
        { hue: FIELD, label: 'the statewide median district' },
        { hue: BAND, label: 'the middle half of all Massachusetts districts' },
      ]} />
    </div>
  )
}

/* ------------------------------------------- 2. the six districts, one year, per pupil */

export type YearRow = {
  fy: number; lea: string; district: string; total: number; gen_fund: number
  grants_revolving: number; grant_share: number; per_pupil: number
  fte_total: number; fte_in_district: number; rank: number; of: number
}

/** One year, six districts, sorted. A bar chart because these are six separate places and
 *  not a series, and the ORDER is the point — but the colour is not: only Lunenburg is
 *  distinguished, because the page's own argument is that the other five are a field we
 *  chose and not a ranking that means anything by itself. */
export function OneYear({ rows, median }: { rows: YearRow[]; median: number }) {
  const data = rows.map(r => ({ ...r, name: shortName(r.district) }))
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} stroke="var(--axis)" interval={0}
              angle={-30} textAnchor="end" height={72} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54} tickFormatter={compact} />
            <ReferenceLine y={median} stroke={FIELD} strokeDasharray="4 3"
              strokeWidth={1.5} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as YearRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{p.district}</div>
                  <div className="font-semibold">{money(p.per_pupil)} a pupil</div>
                  <div>{money(p.total)} across {p.fte_total.toLocaleString()} FTE pupils</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    {pct1(p.grant_share)} of it grants and revolving funds
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="per_pupil" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map(d => (
                <Cell key={d.district} fill={d.lea === '01620000' ? OURS : FIELD} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg' },
        { hue: FIELD, label: 'the five comparison districts — a set we chose, not DESE’s' },
      ]} />
    </div>
  )
}

/* ------------------------------------- 3. the decomposition: money against pupils */

export type DecompRow = {
  district: string; is_lunenburg: boolean
  spend_from: number; spend_to: number; spend_pct: number
  pupils_from: number; pupils_to: number; pupils_pct: number
  per_pupil_from: number; per_pupil_to: number; per_pupil_pct: number
  at_old_enrollment: number; rank_at_old_enrollment: number
}

/** THE PAGE'S CENTRAL CHART. Two bars per district — how much more it spent, and how many
 *  fewer pupils it has — because (1 + spending) ÷ (1 + pupils) = (1 + per pupil) exactly,
 *  and a reader who sees the two halves side by side can see which one is doing the work.
 *
 *  A grouped bar and not a stack: they are not parts of a whole, they are a numerator and
 *  a denominator, and stacking them would assert an addition that is not true.
 *
 *  Zero is always drawn, because one series is negative in every district and the other
 *  positive in every district, and that fact IS the finding. */
export function MoneyAgainstPupils({ rows }: { rows: DecompRow[] }) {
  const data = rows.map(r => ({ ...r, name: shortName(r.district) }))
  return (
    <div className="mt-5">
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} stroke="var(--axis)" interval={0}
              angle={-30} textAnchor="end" height={72} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={48}
              tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
            <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1.5} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as DecompRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{p.district}</div>
                  <div>Spending {signedPct(p.spend_pct)}</div>
                  <div>FTE pupils {signedPct(p.pupils_pct)}</div>
                  <div className="font-semibold mt-1">
                    Per pupil {signedPct(p.per_pupil_pct)}
                  </div>
                  <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
                    Same money over the older pupil count: {money(p.at_old_enrollment)}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="spend_pct" fill={MONEY} radius={[4, 4, 0, 0]}
              isAnimationActive={false} />
            <Bar dataKey="pupils_pct" fill={PUPILS} radius={[0, 0, 4, 4]}
              isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: MONEY, label: 'change in total spending' },
        { hue: PUPILS, label: 'change in FTE pupils' },
      ]} />
    </div>
  )
}

/* ------------------------------------------- 4. the gap, decomposed by category */

export type CatRow = {
  code: string; desc: string; lunenburg: number; median_peer: number; gap: number
  rank: number; of: number; peer_low: number; peer_high: number; peer_median: number
  by_district: Record<string, number>
}

/** DIVERGING, because the quantity is signed and the sign is a real finding: eight of the
 *  eleven categories run below the comparison district and three run above. One bar per
 *  category, zero always drawn.
 *
 *  A stacked or absolute version would hide the whole point, which is that the gap is
 *  concentrated in six lines and reversed in three. --series-cost below zero and
 *  --series-revenue above is this site's existing diverging pair and it carries no verdict
 *  here: less is not worse, it is less. The caption says so. */
export function CategoryGap({ rows, peer }: { rows: CatRow[]; peer: string }) {
  const data = rows.filter(r => r.gap !== 0).map(r => ({ ...r, name: r.desc }))
  return (
    <div className="mt-5">
      <div style={{ height: 40 + data.length * 34 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical"
            margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={AXIS} stroke="var(--axis)"
              tickFormatter={(v: number) => `${v < 0 ? '−' : ''}$${Math.abs(v)}`} />
            <YAxis type="category" dataKey="name" tick={{ ...AXIS, fontSize: 10.5 }}
              stroke="var(--axis)" width={188} interval={0} />
            <ReferenceLine x={0} stroke="var(--axis)" strokeWidth={1.5} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as CatRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{p.desc}</div>
                  <div>Lunenburg {money(p.lunenburg)} a pupil</div>
                  <div>{shortName(peer)} {money(p.median_peer)}</div>
                  <div className="font-semibold mt-1">{signedUsd(p.gap)} a pupil</div>
                  <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
                    {p.rank} of {p.of} in this set · the five comparison districts run{' '}
                    {money(p.peer_low)}–{money(p.peer_high)}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="gap" radius={3} isAnimationActive={false}>
              {data.map(d => (
                <Cell key={d.code} fill={d.gap < 0 ? OURS : 'var(--series-revenue)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg spends less on this line' },
        { hue: 'var(--series-revenue)', label: 'Lunenburg spends more' },
      ]} />
    </div>
  )
}

/* -------------------------------------- 5. teachers: what they are paid, and how many */

export type TeacherRow = {
  district: string; is_lunenburg: boolean; teacher_fte: number; para_fte: number
  per_hundred: number; average_salary: number; spend: number; per_pupil: number
  spend_per_teacher_fte: number; salary_share_of_spend_per_fte: number
  fte_in_district: number
}

/** Two panels rather than one dual-axis chart, and it is the same rule as everywhere else
 *  on this site: a second y-scale proves whatever the scales were chosen to prove.
 *
 *  Left, what a teacher is paid. Right, how many teachers there are for each hundred
 *  in-district pupils. Reading the two together is the whole section and the reader does
 *  it, rather than a composite mark doing it for them. */
export function TeacherSplit({ rows }: { rows: TeacherRow[] }) {
  const bySalary = [...rows].sort((a, b) => b.average_salary - a.average_salary)
    .map(r => ({ ...r, name: shortName(r.district) }))
  const byRatio = [...rows].sort((a, b) => b.per_hundred - a.per_hundred)
    .map(r => ({ ...r, name: shortName(r.district) }))
  const panel = (
    data: (TeacherRow & { name: string })[], key: 'average_salary' | 'per_hundred',
    fmt: (v: number) => string, title: string,
  ) => (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>{title}</p>
      <div style={{ height: 210 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 6, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 10 }} stroke="var(--axis)"
              interval={0} angle={-35} textAnchor="end" height={70} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={52} tickFormatter={fmt}
              domain={key === 'per_hundred' ? [0, 'auto'] : [0, 'auto']} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as TeacherRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{p.district}</div>
                  <div>Average teacher salary {money(p.average_salary)}</div>
                  <div>{p.teacher_fte.toLocaleString()} teacher FTE</div>
                  <div>{p.per_hundred.toFixed(2)} per 100 in-district FTE pupils</div>
                  <div className="font-semibold mt-1">
                    {money(p.per_pupil)} a pupil on the Teachers line
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey={key} radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map(d => (
                <Cell key={d.district} fill={d.is_lunenburg ? OURS : FIELD} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
  return (
    <div className="mt-5">
      <div className="grid gap-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        {panel(bySalary, 'average_salary', compact, 'What a teacher is paid')}
        {panel(byRatio, 'per_hundred', (v: number) => v.toFixed(1),
          'Teachers per 100 in-district pupils')}
      </div>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg' },
        { hue: FIELD, label: 'the five comparison districts' },
      ]} />
    </div>
  )
}

/* --------------------------------------- 6. the share that is not general-fund money */

/** Rule 11, drawn. Each district's all-funds total split into the general fund and
 *  everything else — grants, revolving funds, school choice, gifts. Stacked, because these
 *  two DO add to the total and a reader should be able to see that they do.
 *
 *  It is here because every other chart on this page is a per-pupil figure computed over
 *  this total, and a reader who takes those figures for "what the town pays" has taken
 *  them for something else. */
export function FundSplit({ rows }: { rows: YearRow[] }) {
  const data = [...rows].sort((a, b) => b.grant_share - a.grant_share)
    .map(r => ({ ...r, name: shortName(r.district) }))
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={AXIS} stroke="var(--axis)" interval={0}
              angle={-30} textAnchor="end" height={72} />
            <YAxis tick={AXIS} stroke="var(--axis)" width={54} tickFormatter={compact} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              const p = payload?.[0]?.payload as YearRow | undefined
              if (!active || !p) return null
              return (
                <Box>
                  <div className="font-bold mb-1">{p.district}</div>
                  <div>General fund {money(p.gen_fund)}</div>
                  <div>Grants and revolving {money(p.grants_revolving)}</div>
                  <div className="font-semibold mt-1">
                    {pct1(p.grant_share)} of {money(p.total)}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="gen_fund" stackId="a" fill={FIELD} isAnimationActive={false} />
            <Bar dataKey="grants_revolving" stackId="a" fill={MONEY}
              radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: FIELD, label: 'general fund' },
        { hue: MONEY, label: 'grants, revolving funds, school choice and gifts' },
      ]} />
    </div>
  )
}
