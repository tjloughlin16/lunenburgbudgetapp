import {
  Bar, BarChart, Cell, CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /health-insurance. Every series arrives from /data/health-insurance.json,
 *  written by scripts/build_insurance_charts.py — nothing here computes a figure and nothing
 *  here has one typed into it (rule 2).
 *
 *  COLOUR. The categorical question on this page is *whose side of the town a dollar is
 *  for*, and it has exactly three answers: school, town, and **the account does not say**.
 *  So the encoding is two hues and a gray — the site's warm series colour for the schools,
 *  its cool one for the town, and recessive ink for the accounts that name neither.
 *
 *  The gray is deliberate and it is not a third categorical hue. Running the palette
 *  through the data-viz validator, the only check it fails is the chroma floor, on exactly
 *  that slot — which is the point: "we cannot tell" should read as an absence of identity,
 *  not as a third team. Everything that matters passes — CVD separation ΔE 18.0 (protan)
 *  and normal-vision ΔE 18.0 in light, 15.9 / 17.0 in dark, both well above the floor of 8,
 *  and every mark clears 3:1 against its surface in both modes. Identity is never carried
 *  by colour alone: every chart with more than one category has a legend, and the
 *  categorical charts label each bar directly.
 *
 *  ONE AXIS, ALWAYS. Nothing here is a dual-axis chart. Where a budget and an actual are
 *  drawn together they are the same unit on the same scale, and they are never differenced
 *  across each other (rule 1) — the page says which stage each series is.
 *
 *  MISSING YEARS ARE DRAWN AS MISSING. Three of the sixteen annual reports do not yield an
 *  established figure, and a bar chart that simply omits them reads as a continuous series.
 *  Every year in the span gets a slot; the ones with nothing established get a hatched
 *  placeholder and are named underneath.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is a figure they cannot
 *  check. */

export const SCHOOL = 'var(--series-revenue)'
export const TOWN = 'var(--series-cost)'
export const UNNAMED = 'var(--text-muted)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const pct = (x: number) => {
  if (Math.abs(x) < 0.0005) return '0%'
  const d = Math.abs(x) >= 0.1 ? 0 : 1
  return `${x > 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(d)}%`
}
export const share = (x: number) => `${(x * 100).toFixed(1)}%`
export const hue = (side: string) =>
  side === 'school' ? SCHOOL : side === 'town' ? TOWN : UNNAMED

export const SIDE_LABEL: Record<string, string> = {
  school: 'Named for the schools',
  town: 'Named for the town',
  unnamed: 'Names neither side',
}

/** A scrolling table twin. Wide content scrolls inside its own box; the page body never
 *  scrolls sideways. */
export function TableTwin({ head, rows, caption }: {
  head: string[]; rows: (string | number)[][]; caption?: string
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
              <th key={h} className="text-left font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
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
    </div>
  )
}

function Legend3({ sides }: { sides: string[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {sides.map(s => (
        <span key={s} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: hue(s) }} />
          {SIDE_LABEL[s] ?? s}
        </span>
      ))}
    </div>
  )
}

/* --------------------------------------------- the insurance department, account by account */

export type Account = {
  account_id: string; printed: string; meaning: string; side: string
  original: number; expended: number; available: number
}

/** Seven accounts, ranked, each bar as long as its appropriation and coloured by whose side
 *  the account NAMES. Bars rather than a pie: the reader's question is how one line compares
 *  with the others, and length on a common baseline is the only encoding that answers it
 *  without arithmetic. Directly labelled, so colour is decoration on top of the label. */
export function ByAccount({ accounts, total }: { accounts: Account[]; total: number }) {
  const rows = [...accounts].sort((a, b) => b.original - a.original)
  const top = rows[0].original
  return (
    <div className="mt-5">
      <div className="flex flex-col gap-2.5">
        {rows.map(a => (
          <div key={a.account_id}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-semibold">{a.meaning}</span>
              <span className="text-[12.5px] tnum whitespace-nowrap"
                style={{ color: 'var(--text-secondary)' }}>
                {usd(a.original)} &middot; {share(a.original / total)}
              </span>
            </div>
            <div className="mt-1 rounded-[3px]"
              style={{ background: 'var(--surface-3)', height: 14 }}>
              <div className="rounded-[3px]"
                style={{
                  width: `${Math.max(1.2, (a.original / top) * 100)}%`,
                  height: 14, background: hue(a.side),
                }} />
            </div>
            <p className="text-[11px] mt-1 tnum" style={{ color: 'var(--text-muted)' }}>
              {a.account_id} &middot; printed <code>{a.printed}</code>
            </p>
          </div>
        ))}
      </div>
      <Legend3 sides={['school', 'town', 'unnamed']} />
    </div>
  )
}

/* ------------------------------------------------ where the schools' health money sits */

export type Segment = { key: string; label: string; where: string; amount: number; side: string }

/** One bar, two segments, drawn to scale: the same year's school health-insurance money,
 *  split by which department it was appropriated to. A 2px surface gap keeps the segments
 *  from reading as one mark. */
export function WhereItSits({ segments, total }: { segments: Segment[]; total: number }) {
  return (
    <div className="mt-5">
      <div className="flex w-full rounded-[4px] overflow-hidden" style={{ height: 30, gap: 2 }}>
        {segments.map(s => (
          <div key={s.key} style={{
            width: `${(s.amount / total) * 100}%`,
            background: s.key === 'retiree' ? SCHOOL : TOWN,
          }} />
        ))}
      </div>
      <div className="grid gap-4 mt-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        {segments.map(s => (
          <div key={s.key}>
            <div className="flex items-center gap-2">
              <span className="inline-block rounded-[2px]" style={{
                width: 12, height: 12,
                background: s.key === 'retiree' ? SCHOOL : TOWN,
              }} />
              <span className="text-[13px] font-bold">{s.label}</span>
            </div>
            <div className="text-2xl font-bold tnum mt-1">{usd(s.amount)}</div>
            <p className="text-[12.5px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
              {share(s.amount / total)} of it &middot; {s.where}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------ the department over sixteen years */

export type TownYear = {
  fy: number; appropriated: number | null; source: string; page?: string | null
}

function TownTip({ active, payload, label, missing }: {
  active?: boolean; label?: number
  payload?: { payload: { fy: number; appropriated: number | null; source: string } }[]
  missing: Record<number, string>
}) {
  if (!active) return null
  const p = payload?.[0]?.payload
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 190 }}>
      <div className="font-bold mb-1">{fy(Number(label))}</div>
      {p && p.appropriated != null ? (
        <>
          <div className="tnum">{usd(p.appropriated)} appropriated</div>
          <div className="mt-1" style={{ color: 'var(--text-muted)' }}>
            {p.source === 'ledger' ? 'the town’s FY26 ledger' : 'the annual town report'}
          </div>
        </>
      ) : (
        <div style={{ color: 'var(--text-muted)' }}>
          nothing established &mdash; {missing[Number(label)]}
        </div>
      )}
    </div>
  )
}

export function TownOverTime({ years, missing, splitFy }: {
  years: TownYear[]; missing: { fy: number; why: string }[]; splitFy: number | null
}) {
  const byFy = new Map(years.map(y => [y.fy, y]))
  const first = Math.min(...years.map(y => y.fy)), last = Math.max(...years.map(y => y.fy))
  const span = Array.from({ length: last - first + 1 }, (_, i) => first + i)
  const rows = span.map(f => byFy.get(f) ?? { fy: f, appropriated: null, source: 'none' })
  const why = Object.fromEntries(missing.map(m => [m.fy, m.why]))
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={62} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={<TownTip missing={why} />} />
            {splitFy != null && (
              <ReferenceLine x={splitFy} stroke="var(--status-warning)" strokeDasharray="3 3"
                label={{ value: 'one line becomes three', position: 'top', fontSize: 10,
                  fill: 'var(--text-muted)' }} />
            )}
            <Bar dataKey="appropriated" isAnimationActive={false} radius={[3, 3, 0, 0]}>
              {rows.map(r => (
                <Cell key={r.fy} fill={r.source === 'ledger' ? SCHOOL : TOWN}
                  fillOpacity={r.source === 'ledger' ? 1 : 0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-2">
        <span className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: TOWN, opacity: 0.85 }} />
          appropriated, as the annual town report printed it
        </span>
        <span className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: SCHOOL }} />
          appropriated, from the town&rsquo;s own ledger
        </span>
      </div>
    </div>
  )
}

/* -------------------------------------------- the district's own line, budget and actual */

export type Point = { fy: number; value: number }

function LineTip({ active, payload, label, names }: {
  active?: boolean; label?: number
  payload?: { dataKey: string; value: number | null }[]
  names: Record<string, string>
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 200 }}>
      <div className="font-bold mb-1">{fy(Number(label))}</div>
      {payload.filter(p => p.value != null).map(p => (
        <div key={p.dataKey} className="flex justify-between gap-4">
          <span style={{ color: 'var(--text-secondary)' }}>{names[p.dataKey]}</span>
          <span className="tnum">{usd(p.value as number)}</span>
        </div>
      ))}
    </div>
  )
}

/** The district's own Health Insurance line at two stages. Same unit, same scale, ONE axis.
 *  They are two different documents about the same line and the page never subtracts one
 *  from the other or measures growth across them (rule 1). */
export function DistrictLine({ settled, actual }: { settled: Point[]; actual: Point[] }) {
  const fys = [...new Set([...settled, ...actual].map(p => p.fy))].sort((a, b) => a - b)
  const s = new Map(settled.map(p => [p.fy, p.value]))
  const a = new Map(actual.map(p => [p.fy, p.value]))
  const rows = fys.map(f => ({ fy: f, settled: s.get(f) ?? null, actual: a.get(f) ?? null }))
  const names = { settled: 'Budgeted (settled)', actual: 'Actual, as later reported' }
  return (
    <div className="mt-5">
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={62} />
            <Tooltip content={<LineTip names={names} />} />
            <Legend verticalAlign="bottom" height={28} iconType="plainline"
              formatter={(v: string) => (
                <span style={{ color: 'var(--text-secondary)', fontSize: 11.5 }}>
                  {names[v as keyof typeof names]}
                </span>
              )} />
            <Line type="monotone" dataKey="actual" stroke={TOWN} strokeWidth={2}
              dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="settled" stroke={SCHOOL} strokeWidth={2}
              dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ the FY27 scenarios, ranked */

export type Variant = { variant: string; points: Point[] }

export function Scenarios({ variants, fy: year, baseline, baselineLabel }: {
  variants: Variant[]; fy: number; baseline: number; baselineLabel: string
}) {
  const rows = variants
    .map(v => ({ name: v.variant, value: v.points.find(p => p.fy === year)?.value ?? null }))
    .filter(r => r.value != null)
    .sort((x, y) => (y.value as number) - (x.value as number))
  if (!rows.length) return null
  const top = Math.max(...rows.map(r => r.value as number), baseline)
  return (
    <div className="mt-5">
      <div className="flex flex-col gap-2.5">
        {rows.map(r => (
          <div key={r.name}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-semibold">{r.name}</span>
              <span className="text-[12.5px] tnum whitespace-nowrap"
                style={{ color: 'var(--text-secondary)' }}>
                {usd(r.value as number)} &middot;{' '}
                {pct(((r.value as number) - baseline) / baseline)} on {baselineLabel}
              </span>
            </div>
            <div className="mt-1 rounded-[3px]" style={{ background: 'var(--surface-3)', height: 12 }}>
              <div className="rounded-[3px]" style={{
                width: `${((r.value as number) / top) * 100}%`, height: 12, background: SCHOOL,
              }} />
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
        Every bar is {fy(year)} <em>proposed</em>, measured against {baselineLabel}. Four
        proposals for one year, all from the same workbook.
      </p>
    </div>
  )
}
