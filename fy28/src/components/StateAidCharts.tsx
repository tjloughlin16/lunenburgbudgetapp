import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /state-aid. Every series arrives from /data/state-aid.json, written by
 *  scripts/build_state_aid.py — nothing here computes a figure and nothing here has one
 *  typed into it (rule 2).
 *
 *  COLOUR. The categorical question on this page is *who decides a dollar*, and it has two
 *  answers: the state, and Lunenburg. So two hues, the site's cool series colour for the
 *  state's half and its warm one for the town's, plus recessive ink for a year that is not
 *  established. Identity is never carried by colour alone — every multi-series chart has a
 *  legend and the split bars are directly labelled.
 *
 *  THE VARIANCE CHART IS DIVERGING, because the quantity is. An estimate can be beaten or
 *  missed, zero is a real and meaningful value, and a sequential ramp would make a $390,814
 *  shortfall look like a small amount of a good thing. Positive and negative get the two
 *  hues and a zero reference line is always drawn.
 *
 *  ONE AXIS, ALWAYS. Nothing here is dual-axis. Where a budget and an actual appear on one
 *  page they are never on one chart, because rule 1 says the difference between them is
 *  partly the step between the stages — the stage is printed on every chart title.
 *
 *  UNPUBLISHED YEARS ARE DRAWN AS GAPS, NEVER AS ZEROS. Seven of the twelve years in the
 *  Chapter 70 receipt span have no established figure, and a bar chart that simply omits
 *  them reads as a continuous series. Every year in the span gets a slot; the ones with
 *  nothing established get a hatched placeholder and are named underneath.
 *
 *  PANELS THAT ARE COMPARED SHARE ONE DENOMINATOR. The nine-town variance panel is drawn in
 *  dollars on one scale for all nine, because the question is how big a swing is against a
 *  town budget and every one of these towns budgets in the same units.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is a figure they cannot
 *  check. */

export const STATE = 'var(--series-cost)'
export const TOWN_HUE = 'var(--series-revenue)'
export const MUTED = 'var(--text-muted)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const share = (x: number) => `${(x * 100).toFixed(1)}%`
export const pct = (x: number) => {
  const d = Math.abs(x) >= 0.1 ? 1 : 2
  return `${x > 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(d)}%`
}
/** Dollars, signed, for a quantity where the sign is the finding. */
export const signed = (n: number) => (n < 0 ? `−${usd(-n)}` : `+${usd(n)}`)

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${n}`

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-3 text-[12.5px]"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      {children}
    </div>
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

/* ------------------------------------------------------ who decides the school dollar */

/** ONE BAR, TWO SEGMENTS, drawn to scale: the school appropriation split into the part
 *  Chapter 70 covers and the part the town raises. This is the page's whole argument in one
 *  mark, so it is a bar and not a donut — two lengths on a common baseline compare without
 *  arithmetic, two arcs do not. */
export function WhoPays({ total, aid, aidLabel, townLabel }: {
  total: number; aid: number; aidLabel: React.ReactNode; townLabel: React.ReactNode
}) {
  const town = total - aid
  return (
    <div className="mt-5">
      <div className="flex w-full rounded-[4px] overflow-hidden" style={{ height: 34, gap: 2 }}>
        <div style={{ width: `${(aid / total) * 100}%`, background: STATE }} />
        <div style={{ width: `${(town / total) * 100}%`, background: TOWN_HUE }} />
      </div>
      <div className="grid gap-4 mt-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 16rem), 1fr))' }}>
        {[
          { hue: STATE, amount: aid, label: aidLabel },
          { hue: TOWN_HUE, amount: town, label: townLabel },
        ].map((s, i) => (
          <div key={i}>
            <div className="flex items-center gap-2">
              <span className="inline-block rounded-[2px]"
                style={{ width: 12, height: 12, background: s.hue }} />
              <span className="text-[13px] font-bold">{share(s.amount / total)}</span>
            </div>
            <div className="text-2xl font-bold tnum mt-1">{usd(s.amount)}</div>
            <p className="text-[12.5px] leading-snug mt-1"
              style={{ color: 'var(--text-secondary)' }}>{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------- Chapter 70 received, with the years missing */

export type ReceiptYear = {
  fy: number; amount: number | null; status: string; why: string | null
  unpublished_figure: number | null; page: string | null
}

/** Every year in the span gets a slot. A year with no established figure is drawn as a
 *  hatched placeholder at the height of the tallest bar, so the eye reads "we do not know"
 *  rather than "it fell to nothing" — the failure mode a plain omission produces. */
export function Receipts({ series }: { series: ReceiptYear[] }) {
  const known = series.filter(r => r.amount != null).map(r => r.amount as number)
  const top = Math.max(...known)
  const data = series.map(r => ({
    fy: fy(r.fy), amount: r.amount, gap: r.amount == null ? top : null,
    status: r.status,
  }))
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <defs>
              <pattern id="sa-gap" width="6" height="6" patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)">
                <rect width="6" height="6" fill="transparent" />
                <line x1="0" y1="0" x2="0" y2="6" stroke="var(--grid)" strokeWidth="3" />
              </pattern>
            </defs>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compact} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const p = payload[0].payload as typeof data[number]
              return (
                <Box>
                  <div className="font-bold">{p.fy}</div>
                  <div className="tnum">
                    {p.amount != null ? usd(p.amount) : 'no established figure'}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="gap" fill="url(#sa-gap)" isAnimationActive={false} />
            <Bar dataKey="amount" fill={STATE} isAnimationActive={false}
              radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: STATE, label: 'Chapter 70 received — reconciled to the report’s own totals' },
        { hue: 'var(--grid)', label: 'No established figure for that year' },
      ]} />
    </div>
  )
}

/* --------------------------------------------------- the estimate error, over five years */

export type VarYear = {
  year: number; amount: number; certified: number | null
  share_of_certified: number | null
}

/** DIVERGING, because the quantity diverges. Above the line the town received more aid than
 *  the tax rate was set on; below it, less. Zero is drawn explicitly — an estimate that came
 *  in exactly right is a real outcome and the reader has to be able to see where it would
 *  sit. */
export function Variance({ series }: { series: VarYear[] }) {
  const data = series.map(r => ({ ...r, label: `FY${String(r.year).slice(2)}` }))
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compact} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const p = payload[0].payload as typeof data[number]
              return (
                <Box>
                  <div className="font-bold">{p.label}</div>
                  <div className="tnum">{signed(p.amount)}</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    {p.amount > 0 ? 'more aid than estimated' : 'less aid than estimated'}
                  </div>
                </Box>
              )
            }} />
            <Bar dataKey="amount" isAnimationActive={false} radius={[2, 2, 0, 0]}>
              {data.map(r => (
                <Cell key={r.year} fill={r.amount >= 0 ? STATE : TOWN_HUE} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: STATE, label: 'More aid arrived than the budget was built on' },
        { hue: TOWN_HUE, label: 'Less aid arrived — the town covered the difference' },
      ]} />
    </div>
  )
}

/* ---------------------------------------------------------- nine towns, one dollar scale */

export type PeerRow = {
  town: string; best: number; worst: number; swing: number; mean_abs: number
  over: number; under: number
}

/** Every town on ONE dollar scale, worst year to best year as a span, sorted by how far
 *  the two are apart. One denominator across all nine panels: dollars. */
export function Peers({ rows, town }: { rows: PeerRow[]; town: string }) {
  const lo = Math.min(...rows.map(r => r.worst), 0)
  const hi = Math.max(...rows.map(r => r.best), 0)
  const span = hi - lo || 1
  const x = (v: number) => ((v - lo) / span) * 100
  return (
    <div className="mt-5">
      <div className="flex flex-col gap-2.5">
        {rows.map(r => {
          const me = r.town === town
          return (
            <div key={r.town}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[13px]"
                  style={{ fontWeight: me ? 700 : 500 }}>{r.town}</span>
                <span className="text-[12px] tnum whitespace-nowrap"
                  style={{ color: 'var(--text-secondary)' }}>
                  {signed(r.worst)} to {signed(r.best)}
                </span>
              </div>
              <div className="relative mt-1 rounded-[3px]"
                style={{ background: 'var(--surface-3)', height: 14 }}>
                <div className="absolute rounded-[3px]" style={{
                  left: `${x(r.worst)}%`, width: `${Math.max(0.8, x(r.best) - x(r.worst))}%`,
                  height: 14, background: me ? TOWN_HUE : 'var(--axis)',
                  opacity: me ? 1 : 0.55,
                }} />
                <div className="absolute" style={{
                  left: `${x(0)}%`, width: 1, height: 14, background: 'var(--text-muted)',
                }} />
              </div>
            </div>
          )
        })}
      </div>
      <Legend items={[
        { hue: TOWN_HUE, label: `${town} — worst year to best year` },
        { hue: 'var(--axis)', label: 'The eight comparison towns, same scale' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------ the formula, both halves */

/** The state's minimum for Lunenburg, split into the half the state pays and the half it
 *  orders the town to pay. Drawn to scale from DESE's own columns F, G and H, whose sum the
 *  generator asserts before this renders. */
export function Formula({ required, aid, nss }: {
  required: number; aid: number; nss: number
}) {
  return (
    <div className="mt-5">
      <div className="flex w-full rounded-[4px] overflow-hidden" style={{ height: 34, gap: 2 }}>
        <div style={{ width: `${(aid / nss) * 100}%`, background: STATE }} />
        <div style={{ width: `${(required / nss) * 100}%`, background: TOWN_HUE }} />
      </div>
      <div className="grid gap-4 mt-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 16rem), 1fr))' }}>
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-block rounded-[2px]"
              style={{ width: 12, height: 12, background: STATE }} />
            <span className="text-[13px] font-bold">{share(aid / nss)}</span>
          </div>
          <div className="text-2xl font-bold tnum mt-1">{usd(aid)}</div>
          <p className="text-[12.5px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
            Chapter 70 aid — the state&rsquo;s half of the minimum
          </p>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-block rounded-[2px]"
              style={{ width: 12, height: 12, background: TOWN_HUE }} />
            <span className="text-[13px] font-bold">{share(required / nss)}</span>
          </div>
          <div className="text-2xl font-bold tnum mt-1">{usd(required)}</div>
          <p className="text-[12.5px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
            Required local contribution — Lunenburg&rsquo;s half, also set by the formula
          </p>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------- state aid in the FY26 revenue ledger */

export type Account = {
  object: string; printed: string; meaning: string; kind: string
  budgeted: number; received: number; pct_received: number | null
}

/** Ranked bars, directly labelled, coloured by whether the account's printed name says
 *  schools. Bars rather than a pie because the reader's question is how one line compares
 *  with the others, and length on a common baseline answers it without arithmetic. */
export function ByAccount({ accounts, total }: { accounts: Account[]; total: number }) {
  const rows = accounts.filter(a => a.budgeted > 0).sort((a, b) => b.budgeted - a.budgeted)
  const top = rows[0]?.budgeted ?? 1
  return (
    <div className="mt-5">
      <div className="flex flex-col gap-2.5">
        {rows.map(a => (
          <div key={a.object}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-semibold">{a.meaning}</span>
              <span className="text-[12.5px] tnum whitespace-nowrap"
                style={{ color: 'var(--text-secondary)' }}>
                {usd(a.budgeted)} &middot; {share(a.budgeted / total)}
              </span>
            </div>
            <div className="mt-1 rounded-[3px]"
              style={{ background: 'var(--surface-3)', height: 14 }}>
              <div className="rounded-[3px]" style={{
                width: `${Math.max(1.2, (a.budgeted / top) * 100)}%`, height: 14,
                background: a.kind === 'school' ? STATE
                  : a.kind === 'local_option' ? MUTED : TOWN_HUE,
              }} />
            </div>
            <p className="text-[11px] mt-1 tnum" style={{ color: 'var(--text-muted)' }}>
              object {a.object} &middot; printed <code>{a.printed}</code>
            </p>
          </div>
        ))}
      </div>
      <Legend items={[
        { hue: STATE, label: 'The printed name says schools' },
        { hue: TOWN_HUE, label: 'The printed name says something else' },
        { hue: MUTED, label: 'Not aid — a local tax the state collects and remits' },
      ]} />
    </div>
  )
}

/* -------------------------------------------------------- four counts of the same children */

export type PupilCount = {
  measure: string; fy: number; value: number; who: string
  is_formula: boolean; whole_district: boolean
}

/** Four published counts on one axis, so the disagreement is a length rather than a
 *  sentence. The out-of-district component is drawn recessive and labelled as a component,
 *  because it is not a rival count of the district. */
export function Pupils({ counts }: { counts: PupilCount[] }) {
  const top = Math.max(...counts.map(c => c.value))
  return (
    <div className="mt-5 flex flex-col gap-2.5">
      {counts.map(c => (
        <div key={c.measure}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px]" style={{ fontWeight: c.is_formula ? 700 : 500 }}>
              {c.measure} <span style={{ color: 'var(--text-muted)' }}>&middot; {fy(c.fy)}</span>
            </span>
            <span className="text-[12.5px] tnum">{c.value.toLocaleString()}</span>
          </div>
          <div className="mt-1 rounded-[3px]" style={{ background: 'var(--surface-3)', height: 14 }}>
            <div className="rounded-[3px]" style={{
              width: `${Math.max(1.2, (c.value / top) * 100)}%`, height: 14,
              background: c.is_formula ? STATE : c.whole_district ? TOWN_HUE : MUTED,
            }} />
          </div>
          <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>{c.who}</p>
        </div>
      ))}
      <Legend items={[
        { hue: STATE, label: 'The count the aid is calculated on' },
        { hue: TOWN_HUE, label: 'Other counts DESE publishes for the same district' },
        { hue: MUTED, label: 'A component of the total, not a rival count' },
      ]} />
    </div>
  )
}

/* ---------------------------------------------------------- the enrollment series, plotted */

export type PupilPoint = { fy: number; measure: string; value: number }

/** Three counts across every year DESE publishes, one axis, three lines. The span is stated
 *  on the chart because a reader must not mistake a short series for a long one. */
export function PupilTrend({ series, measures }: {
  series: PupilPoint[]; measures: string[]
}) {
  const years = [...new Set(series.map(p => p.fy))].sort((a, b) => a - b)
  const data = years.map(y => {
    const row: Record<string, number | string> = { fy: fy(y) }
    for (const m of measures) {
      const p = series.find(s => s.fy === y && s.measure === m)
      if (p) row[m] = p.value
    }
    return row
  })
  const hues = [STATE, TOWN_HUE, MUTED]
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} width={48} />
            <Tooltip content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <Box>
                  <div className="font-bold">{label}</div>
                  {payload.map(p => (
                    <div key={String(p.dataKey)} className="tnum">
                      {String(p.dataKey)}: {Number(p.value).toLocaleString()}
                    </div>
                  ))}
                </Box>
              )
            }} />
            {measures.map((m, i) => (
              <Line key={m} type="monotone" dataKey={m} stroke={hues[i % hues.length]}
                strokeWidth={2} dot={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={measures.map((m, i) => ({ hue: hues[i % hues.length], label: m }))} />
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {years.length} years, FY{String(years[0]).slice(2)}&ndash;FY
        {String(years[years.length - 1]).slice(2)}, as DESE publishes them.
      </p>
    </div>
  )
}
