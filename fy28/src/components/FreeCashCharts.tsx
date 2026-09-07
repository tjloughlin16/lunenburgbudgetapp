import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd, usdShort } from '../model/engine'

/** The charts for /free-cash's drill-in half. Every series arrives from
 *  /data/free-cash.json, written by scripts/build_free_cash_charts.py — nothing here
 *  computes a headline figure and nothing here has one typed into it (rule 2).
 *
 *  ONE DENOMINATOR PER COMPARED PANEL, AND IT IS NEVER DOLLARS ACROSS TOWNS. The DLS
 *  proof carries no population, budget, revenue or levy for any of the nine towns, so
 *  Littleton's $11.3M against Shirley's $272K says nothing about which is closer to its
 *  own target. Every cross-town chart here is a SHARE of that town's own identified free
 *  cash, or a ratio against that town's own average. The absolute-dollar charts are
 *  Lunenburg alone.
 *
 *  A SIGN IS A FINDING, NOT A SECOND COLOUR. Cherry sheet receipts and local receipts can
 *  come in above or below the estimate, and a component below it SUBTRACTS from free cash.
 *  Those bars are drawn in the same hue, below a zero reference line, because the sign is
 *  the whole point and a second hue would state it twice while suggesting two categories.
 *
 *  EVERY CHART HAS A TABLE TWIN. House style and the accessibility floor: a figure a
 *  reader cannot copy out of the page is a figure they cannot check.
 *
 *  A YEAR NOBODY PUBLISHED IS A GAP. The Town's own undesignated fund balance roll-forward
 *  has been read for two years, and the three years before it are drawn as absent rather
 *  than as zero — a bar of height zero would say the balance was nothing. */

export const FC: Record<string, string> = {
  underspend: 'var(--fc-underspend)',
  receipts: 'var(--fc-receipts)',
  aid: 'var(--fc-aid)',
  other: 'var(--fc-other)',
}
export const TOWN_C = 'var(--series-cost)'
export const STATE_C = 'var(--series-revenue)'
export const MUTED = 'var(--text-muted)'

export const yr = (n: number) => String(n)
export const pc = (x: number) => `${(x * 100).toFixed(Math.abs(x) >= 0.1 ? 0 : 1)}%`

export type Part = 'underspend' | 'receipts' | 'aid' | 'other'
export type CompRow = {
  year: number; identified: number; certified: number; gap: number
  underspend: number; receipts: number; aid: number; recycled: number; other: number
  shares: Record<string, number | null>
}
export type PeerRow = {
  town: string
  identified: { year: number; amount: number }[]
  certified: { year: number; amount: number }[]
  unspent_share: { year: number; share: number }[]
  receipts_share: { year: number; share: number }[]
  aid_share: { year: number; share: number }[]
  unspent_mean: number
  receipts_positive: number; receipts_total: number
  aid_positive: number; aid_abs_mean_share: number; aid_max_swing: number
  certified_cv: number
}
export type Multiple = { town: string; latest: number; average: number; multiple: number }
export type Versus = {
  year: number; as_of: string; undesignated: number; identified: number; certified: number
  undesignated_minus_identified: number; identified_minus_certified: number
}

export function Card({ children }: { children: React.ReactNode }) {
  return <div className="card p-4">{children}</div>
}

export function Chip({ color, children, hollow }: {
  color: string; children: React.ReactNode; hollow?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block w-2.5 h-2.5 rounded-[2px]"
        style={hollow ? { border: `1.5px dashed ${color}` } : { background: color }} />
      {children}
    </span>
  )
}

function Tip({ title, rows, foot }: {
  title: string
  rows: { label: string; value: string; colour?: string }[]
  foot?: React.ReactNode
}) {
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>{title}</p>
      {rows.map(r => (
        <p key={r.label} className="flex justify-between gap-4">
          <span style={{ color: r.colour ?? 'var(--text-secondary)' }}>{r.label}</span>
          <span className="tnum font-semibold">{r.value}</span>
        </p>
      ))}
      {foot ? (
        <p className="mt-1 pt-1 border-t text-[11px]"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>{foot}</p>
      ) : null}
    </div>
  )
}

const TH = 'font-semibold py-1.5 text-right'
const TH_L = 'font-semibold py-1.5'

/* ------------------------------------------------------- 1. where it comes from */

/** Lunenburg's free cash, by what produced it, every year the proof covers.
 *
 *  Stacked because the components ARE the parts of one total — that is what makes the
 *  workbook a proof rather than a summary, and the sum of the segments is a figure DLS
 *  prints itself. Negative segments stack below the zero line, which is where a year the
 *  state paid less than it estimated belongs. The certified figure rides over the stack
 *  as a line because it is NOT the total of these bars: DLS certifies a different amount,
 *  and drawing it as one more segment would hide exactly the thing this page found. */
export function Composition({ rows, labels }: {
  rows: CompRow[]; labels: Record<string, string>
}) {
  const order: Part[] = ['underspend', 'receipts', 'aid', 'other']
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        {order.map(k => (
          <Chip key={k} color={FC[k]}>
            {labels[k] ?? 'Everything else, net'}
          </Chip>
        ))}
        <Chip color={STATE_C} hollow>what DLS actually certified</Chip>
      </div>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} interval={0} />
            <YAxis width={58} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as CompRow
                return (
                  <Tip title={`1 July ${d.year}`}
                    rows={[
                      ...order.map(k => ({
                        label: labels[k] ?? 'Everything else, net',
                        value: usd(d[k]), colour: FC[k],
                      })),
                      { label: 'Identified free cash', value: usd(d.identified) },
                      { label: 'Certified', value: usd(d.certified), colour: STATE_C },
                    ]}
                    foot={`DLS certified ${usd(Math.abs(d.gap))} ${d.gap > 0 ? 'less' : 'more'} than its own proof identifies`} />
                )
              }} />
            {order.map(k => (
              <Bar key={k} dataKey={k} stackId="a" fill={FC[k]} isAnimationActive={false}
                maxBarSize={54} />
            ))}
            <Line type="linear" dataKey="certified" stroke={STATE_C} strokeWidth={2}
              strokeDasharray="5 4" dot={{ r: 3, fill: STATE_C }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="stack w-full text-xs mt-4 tnum">
          <caption className="sr-only">
            Lunenburg free cash by component, 1 July, as certified by the Division of Local
            Services
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>1 July</th>
              {order.map(k => (
                <th key={k} className={TH}>{labels[k] ?? 'Else, net'}</th>
              ))}
              <th className={TH}>Prior year&rsquo;s free cash</th>
              <th className={TH}>Identified</th>
              <th className={TH}>Certified</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.year} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 font-semibold">{r.year}</td>
                {order.map(k => (
                  <td key={k} className="py-1.5 text-right">
                    {usd(r[k])}
                    <span className="ml-1" style={{ color: 'var(--text-muted)' }}>
                      {r.shares[k] === null ? '' : pc(r.shares[k] as number)}
                    </span>
                  </td>
                ))}
                <td className="py-1.5 text-right">{usd(r.recycled)}</td>
                <td className="py-1.5 text-right font-semibold">{usd(r.identified)}</td>
                <td className="py-1.5 text-right" style={{ color: STATE_C }}>
                  {usd(r.certified)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        The prior year&rsquo;s unappropriated free cash is inside &ldquo;everything else,
        net&rdquo; on the chart and shown separately in the table: it is free cash arriving
        for a second time, so five years of these totals is not five years of new money.
      </p>
    </Card>
  )
}

/* --------------------------------------------- 2. three numbers for the same date */

/** The Town's undesignated fund balance, DLS's identified free cash, and DLS's certified
 *  free cash — same balance sheet, same 30 June, three figures.
 *
 *  A year with no Town roll-forward read is drawn as an absent bar, not a zero one. The
 *  balance existed in those years; nobody has read the page it is printed on. */
export function ThreeNumbers({ rows, versus }: { rows: CompRow[]; versus: Versus[] }) {
  const byYear = new Map(versus.map(v => [v.year, v]))
  const data = rows.map(r => ({
    year: r.year,
    undesignated: byYear.get(r.year)?.undesignated ?? null,
    identified: r.identified,
    certified: r.certified,
    read: byYear.has(r.year),
  }))
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={TOWN_C}>the Town&rsquo;s undesignated fund balance</Chip>
        <Chip color={FC.underspend}>free cash DLS identifies</Chip>
        <Chip color={STATE_C}>free cash DLS certifies</Chip>
        <Chip color={MUTED} hollow>Town roll-forward not read for this year</Chip>
      </div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} interval={0} />
            <YAxis width={58} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as typeof data[number]
                return (
                  <Tip title={`30 June ${d.year}`}
                    rows={[
                      {
                        label: 'Town: undesignated fund balance',
                        value: d.undesignated === null ? 'not read' : usd(d.undesignated),
                        colour: TOWN_C,
                      },
                      { label: 'DLS: identified', value: usd(d.identified), colour: FC.underspend },
                      { label: 'DLS: certified', value: usd(d.certified), colour: STATE_C },
                    ]}
                    foot={d.undesignated === null
                      ? 'The Town publishes a roll-forward; this project has not read this year’s'
                      : 'No document in this archive prints a line between any pair of these'} />
                )
              }} />
            <Bar dataKey="undesignated" fill={TOWN_C} isAnimationActive={false} maxBarSize={26} />
            <Bar dataKey="identified" fill={FC.underspend} isAnimationActive={false} maxBarSize={26} />
            <Bar dataKey="certified" isAnimationActive={false} maxBarSize={26}>
              {data.map(d => <Cell key={d.year} fill={STATE_C} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="stack w-full text-xs mt-4 tnum">
          <caption className="sr-only">
            The Town&rsquo;s undesignated fund balance against the Division of Local
            Services&rsquo; identified and certified free cash, same date
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>30 June</th>
              <th className={TH}>Town: undesignated fund balance</th>
              <th className={TH}>DLS: identified</th>
              <th className={TH}>DLS: certified</th>
              <th className={TH}>Town &minus; identified</th>
              <th className={TH}>Identified &minus; certified</th>
            </tr>
          </thead>
          <tbody>
            {data.map(d => {
              const v = byYear.get(d.year)
              return (
                <tr key={d.year} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1.5 font-semibold">{d.year}</td>
                  <td className="py-1.5 text-right">
                    {d.undesignated === null
                      ? <span style={{ color: 'var(--text-muted)' }}>not read</span>
                      : usd(d.undesignated)}
                  </td>
                  <td className="py-1.5 text-right">{usd(d.identified)}</td>
                  <td className="py-1.5 text-right">{usd(d.certified)}</td>
                  <td className="py-1.5 text-right">
                    {v ? usd(v.undesignated_minus_identified)
                      : <span style={{ color: 'var(--text-muted)' }}>&mdash;</span>}
                  </td>
                  <td className="py-1.5 text-right">
                    {usd(rows.find(r => r.year === d.year)!.gap)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

/* --------------------------------------------------------- 3. the nine-town set */

/** What each town's free cash is MADE of, in one year. One denominator per bar and it is
 *  that town's own identified free cash, so the panels compare. The level does not and is
 *  not drawn: the proof carries no budget, levy, revenue or population for anybody. */
export function PeerComposition({ peers, year }: { peers: PeerRow[]; year: number }) {
  const at = (xs: { year: number; share: number }[]) =>
    xs.find(x => x.year === year)?.share ?? 0
  const data = peers.map(p => {
    const u = at(p.unspent_share), r = at(p.receipts_share), a = at(p.aid_share)
    return { town: p.town, underspend: u, receipts: r, aid: a, other: 1 - u - r - a }
  }).sort((x, y) => y.underspend - x.underspend)
  const order: Part[] = ['underspend', 'receipts', 'aid', 'other']
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={FC.underspend}>appropriated and not spent</Chip>
        <Chip color={FC.receipts}>local receipts above estimate</Chip>
        <Chip color={FC.aid}>state aid against estimate</Chip>
        <Chip color={FC.other}>everything else, net</Chip>
      </div>
      <div style={{ width: '100%', height: Math.max(260, data.length * 30 + 40) }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical"
            margin={{ top: 4, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tickFormatter={v => pc(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis type="category" dataKey="town" width={78}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} interval={0} />
            <ReferenceLine x={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as typeof data[number]
                return (
                  <Tip title={`${d.town} · 1 July ${year}`}
                    rows={order.map(k => ({
                      label: k === 'other' ? 'Everything else, net'
                        : k === 'underspend' ? 'Appropriated and not spent'
                          : k === 'receipts' ? 'Local receipts above estimate'
                            : 'State aid against estimate',
                      value: pc(d[k]), colour: FC[k],
                    }))}
                    foot="Share of that town’s own identified free cash" />
                )
              }} />
            {order.map(k => (
              <Bar key={k} dataKey={k} stackId="a" fill={FC[k]} isAnimationActive={false}
                maxBarSize={20} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="stack w-full text-xs mt-4 tnum">
          <caption className="sr-only">
            What each town&rsquo;s free cash is made of, as a share of its own identified
            free cash
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>Town</th>
              <th className={TH}>Not spent</th>
              <th className={TH}>Local receipts</th>
              <th className={TH}>State aid</th>
              <th className={TH}>Else, net</th>
              <th className={TH}>Its own identified free cash</th>
            </tr>
          </thead>
          <tbody>
            {data.map(d => {
              const p = peers.find(x => x.town === d.town)!
              return (
                <tr key={d.town} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1.5 font-semibold">{d.town}</td>
                  {order.map(k => (
                    <td key={k} className="py-1.5 text-right">{pc(d[k])}</td>
                  ))}
                  <td className="py-1.5 text-right" style={{ color: 'var(--text-muted)' }}>
                    {usd(p.identified.find(i => i.year === year)?.amount ?? 0)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        The last column is there to be read and NOT compared. Nothing in the proof gives any
        town&rsquo;s budget, levy, revenue or population, so a bigger number is not a bigger
        reserve relative to anything.
      </p>
    </Card>
  )
}

/* -------------------------------------------------- 4. was the record year unusual */

/** 2025's unspent appropriations against each town's OWN four-year average. A ratio, so it
 *  compares across towns of any size — and 1.0 is the line that means "an ordinary year". */
export function Multiples({ rows, year, base }: {
  rows: Multiple[]; year: number; base: string
}) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={FC.underspend}>above its own {base} average</Chip>
        <Chip color={MUTED}>below it</Chip>
      </div>
      <div style={{ width: '100%', height: Math.max(240, rows.length * 28 + 40) }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical"
            margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false}
              tickFormatter={v => `${(v as number).toFixed(1)}×`} />
            <YAxis type="category" dataKey="town" width={78}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} interval={0} />
            <ReferenceLine x={1} stroke="var(--axis)" strokeDasharray="4 4" />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as Multiple
                return (
                  <Tip title={d.town}
                    rows={[
                      { label: `${year} not spent`, value: usd(d.latest) },
                      { label: `its own ${base} average`, value: usd(d.average) },
                      { label: 'multiple', value: `${d.multiple.toFixed(2)}×` },
                    ]}
                    foot="A ratio against the town’s own history — it compares; the dollars do not" />
                )
              }} />
            <Bar dataKey="multiple" isAnimationActive={false} maxBarSize={18}>
              {rows.map(r => (
                <Cell key={r.town} fill={r.multiple >= 1 ? FC.underspend : MUTED} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="stack w-full text-xs mt-4 tnum">
          <caption className="sr-only">
            Unspent appropriations in {year} against each town&rsquo;s own {base} average
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>Town</th>
              <th className={TH}>{year} not spent</th>
              <th className={TH}>Its own {base} average</th>
              <th className={TH}>Multiple</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.town} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 font-semibold">{r.town}</td>
                <td className="py-1.5 text-right">{usd(r.latest)}</td>
                <td className="py-1.5 text-right">{usd(r.average)}</td>
                <td className="py-1.5 text-right font-semibold">{r.multiple.toFixed(2)}&times;</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

/* --------------------------------------------------- 5. the cherry sheet, both ways */

/** State aid against the estimate, Lunenburg, in dollars — the one component that goes
 *  NEGATIVE, drawn below a zero line in the same hue rather than in a second colour. The
 *  table twin carries all nine towns, because the interesting thing is comparative: how
 *  often it goes each way, and how far it moves between two consecutive years. */
export function AidSwing({ rows, peers, town }: {
  rows: CompRow[]; peers: PeerRow[]; town: string
}) {
  const data = rows.map(r => ({ year: r.year, aid: r.aid }))
  const ranked = [...peers].sort((a, b) => b.aid_max_swing - a.aid_max_swing)
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={FC.aid}>
          {town}: state aid received against what the budget estimated
        </Chip>
      </div>
      <div style={{ width: '100%', height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} interval={0} />
            <YAxis width={58} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as { year: number; aid: number }
                return (
                  <Tip title={`1 July ${d.year}`}
                    rows={[{ label: 'Cherry sheet, against estimate', value: usd(d.aid), colour: FC.aid }]}
                    foot={d.aid < 0
                      ? 'The state paid LESS than the budget assumed, and free cash is smaller for it'
                      : 'The state paid more than the budget assumed'} />
                )
              }} />
            <Bar dataKey="aid" fill={FC.aid} isAnimationActive={false} maxBarSize={54} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="stack w-full text-xs mt-4 tnum">
          <caption className="sr-only">
            Cherry sheet receipts against estimate: how often each town gained and how far
            the line moves between years
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>Town</th>
              <th className={TH}>Years above estimate</th>
              <th className={TH}>Mean size, as a share of its free cash</th>
              <th className={TH}>Largest move between two years</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map(p => (
              <tr key={p.town} className="border-t"
                style={{ borderColor: 'var(--grid)',
                  fontWeight: p.town === town ? 700 : 400 }}>
                <td className="py-1.5">{p.town}</td>
                <td className="py-1.5 text-right">{p.aid_positive} of {p.aid_share.length}</td>
                <td className="py-1.5 text-right">{pc(p.aid_abs_mean_share)}</td>
                <td className="py-1.5 text-right">{usd(p.aid_max_swing)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
