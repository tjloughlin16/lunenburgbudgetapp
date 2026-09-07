import {
  BarChart, Bar, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /school-staffing. Every series arrives from /data/school-staffing.json,
 *  written by scripts/build_staffing_charts.py — nothing here computes a figure and
 *  nothing here has one typed into it (rule 2).
 *
 *  COLOUR. This page never uses colour to mean "which district". Seven districts is past
 *  the point where categorical hues stay separable under colour-vision deficiency, and a
 *  generated eighth hue is the anti-pattern. So the peer charts use an EMPHASIS encoding
 *  instead — one subject line in the site's warm series colour, every comparison district
 *  in recessive ink — which needs exactly two legend entries and is readable at any number
 *  of peers. The subject line is also directly labelled, so identity never rests on colour.
 *
 *  Where two measures ARE compared they are indexed to a common base and drawn on ONE
 *  axis, using the site's validated diverging pair doing categorical duty. There is no
 *  dual-axis chart on this page: two y-scales is the single most common chart mistake and
 *  it would be especially dishonest here, where the reader's whole question is whether two
 *  things moved together.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is a figure they
 *  cannot check. */

export const SUBJECT = 'var(--series-revenue)'
export const PEER = 'var(--axis)'
export const COOL = 'var(--series-cost)'
export const NEUTRAL = 'var(--text-muted)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const num = (x: number, d = 1) => x.toFixed(d)
export const pct = (x: number) => {
  if (Math.abs(x) < 0.0005) return '0%'
  const d = Math.abs(x) >= 0.1 ? 0 : 1
  return `${x > 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(d)}%`
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="card p-4">{children}</div>
}

function Chip({ color, dashed, children }: {
  color: string; dashed?: boolean; children: React.ReactNode
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block rounded-[2px]"
        style={{
          width: 14, height: 3, background: dashed ? 'transparent' : color,
          borderTop: dashed ? `3px dotted ${color}` : undefined,
        }} />
      {children}
    </span>
  )
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
              <th key={h} className="text-left font-semibold py-1.5 pr-4 whitespace-nowrap
                                     border-b"
                style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right' }}>{h}</th>
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

/* ------------------------------------------------- Lunenburg against its peer districts */

export type PeerPoint = { fy: number; paras_per_100: number | null; teachers_per_100: number | null }
export type Peer = {
  district: string; is_lunenburg: boolean; first_fy: number; last_fy: number
  points: PeerPoint[]
}

function PeerTip({ active, label, field, peers, unit }: {
  active?: boolean; label?: number; field: keyof PeerPoint; peers: Peer[]; unit: string
}) {
  if (!active || label === undefined) return null
  const at = peers
    .map(p => ({ d: p.district, lb: p.is_lunenburg,
      v: p.points.find(q => q.fy === label)?.[field] as number | null | undefined }))
    .filter(r => r.v !== null && r.v !== undefined)
    .sort((a, b) => (b.v as number) - (a.v as number))
  if (!at.length) return null
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {fy(label)} &middot; {unit}
      </p>
      {at.map(r => (
        <p key={r.d} className="flex justify-between gap-5">
          <span style={{ color: r.lb ? SUBJECT : 'var(--text-secondary)',
            fontWeight: r.lb ? 700 : 400 }}>{r.d}</span>
          <span className="tnum" style={{ fontWeight: r.lb ? 700 : 400 }}>
            {num(r.v as number, 2)}
          </span>
        </p>
      ))}
    </div>
  )
}

/** One ratio, Lunenburg against every district on DESE's comparison sheet.
 *
 *  Emphasis rather than category: the reader's question is where ONE district sits, and
 *  seven hues would answer a question nobody asked while failing the CVD separation check.
 *  Peers are drawn first so the subject line is never overdrawn. */
export function PeerRatio({ peers, field, unit, subject }: {
  peers: Peer[]; field: 'paras_per_100' | 'teachers_per_100'; unit: string; subject: string
}) {
  const years = [...new Set(peers.flatMap(p => p.points.map(q => q.fy)))].sort((a, b) => a - b)
  const data = years.map(y => {
    const row: Record<string, number | null> = { fy: y }
    for (const p of peers) row[p.district] = p.points.find(q => q.fy === y)?.[field] ?? null
    return row
  })
  const all = peers.flatMap(p => p.points.map(q => q[field])).filter((v): v is number => v !== null)
  const top = Math.ceil(Math.max(...all) * 1.08 * 2) / 2
  const others = peers.filter(p => !p.is_lunenburg)
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        <Chip color={SUBJECT}>{subject}</Chip>
        <Chip color={PEER}>{others.length} comparison districts</Chip>
      </div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 10, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" interval="preserveStartEnd" minTickGap={18} />
            <YAxis domain={[0, top]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" width={44} />
            <Tooltip content={<PeerTip peers={peers} field={field} unit={unit} />}
              cursor={{ stroke: 'var(--axis)' }} />
            {others.map(p => (
              <Line key={p.district} type="monotone" dataKey={p.district} dot={false}
                stroke={PEER} strokeWidth={1.5} connectNulls={false} isAnimationActive={false} />
            ))}
            <Line type="monotone" dataKey={subject} dot={false} stroke={SUBJECT}
              strokeWidth={2.5} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        {unit}. Every district on DESE&rsquo;s own comparison sheet.
      </p>
    </Card>
  )
}

/* ------------------------------------------------------ two dollar series, indexed */

export type IndexSeries = {
  key: string; label: string; points: { fy: number; dollars: number }[]
}

function IndexTip({ active, label, series }: {
  active?: boolean; label?: number; series: IndexSeries[]
}) {
  if (!active || label === undefined) return null
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {fy(label)}
      </p>
      {series.map((s, i) => {
        const p = s.points.find(q => q.fy === label)
        const base = s.points[0]
        if (!p) return null
        return (
          <p key={s.key} className="flex justify-between gap-5">
            <span style={{ color: i === 0 ? SUBJECT : COOL }}>{s.label}</span>
            <span className="tnum font-semibold">
              {usd(p.dollars)} &middot; {Math.round(100 * p.dollars / base.dollars)}
            </span>
          </p>
        )
      })}
    </div>
  )
}

/** Two dollar series that differ by a factor of three, indexed to their shared first year.
 *
 *  Indexed, not dual-axis. The question is which one grew faster, and putting a $1.8M
 *  series and a $600k series on two scales makes any answer available to whoever chose the
 *  scales. Both raw series are in the table underneath. */
export function IndexedPair({ series }: { series: IndexSeries[] }) {
  const years = series[0].points.map(p => p.fy)
  const data = years.map(y => {
    const row: Record<string, number> = { fy: y }
    for (const s of series) {
      const p = s.points.find(q => q.fy === y)
      if (p) row[s.key] = 100 * p.dollars / s.points[0].dollars
    }
    return row
  })
  const hues = [SUBJECT, COOL]
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        {series.map((s, i) => <Chip key={s.key} color={hues[i]}>{s.label}</Chip>)}
      </div>
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 10, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" minTickGap={14} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)"
              width={44} />
            <ReferenceLine y={100} stroke="var(--axis)" strokeDasharray="3 3" />
            <Tooltip content={<IndexTip series={series} />} cursor={{ stroke: 'var(--axis)' }} />
            {series.map((s, i) => (
              <Line key={s.key} type="monotone" dataKey={s.key} dot={{ r: 3 }}
                stroke={hues[i]} strokeWidth={2.5} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        Both series set to 100 in {fy(years[0])}. The dollars themselves are in the table.
      </p>
    </Card>
  )
}

/* --------------------------------------------------------- names printed, year by year */

export type RosterYear = {
  fy: number; names: number; names_high: number | null; names_if_summed: number | null
  schools: string[]; pages: number; central_office_printed: boolean
  doubled: boolean; shared_names: number
}

function RosterTip({ active, payload }: { active?: boolean; payload?: { payload: RosterYear }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs max-w-[16rem]"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>{fy(d.fy)}</p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Names printed</span>
        <span className="tnum font-bold">
          {d.names}{d.names_high ? `–${d.names_high}` : ''}
        </span>
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Rosters printed</span>
        <span className="tnum">{d.schools.length} · {d.pages} pages</span>
      </p>
      <p className="mt-1.5 leading-snug" style={{ color: 'var(--text-muted)' }}>
        {d.schools.join(', ')}
      </p>
      {d.doubled && (
        <p className="mt-1.5 leading-snug" style={{ color: 'var(--status-warning)' }}>
          Two complete rosters printed for one school. Shown as a range.
        </p>
      )}
    </div>
  )
}

/** How many names the town printed, by year. A bar, because each year is an independent
 *  count off a different document rather than a continuous quantity — a line would draw
 *  a trend through a series whose year-to-year moves are partly print practice.
 *
 *  A year with an unresolved double roster is drawn to its LOW figure with the band above
 *  it hatched, so the uncertainty is in the mark and not only in the footnote. */
export function NamesPrinted({ rows }: { rows: RosterYear[] }) {
  const top = Math.max(...rows.map(r => r.names_high ?? r.names))
  const data = rows.map(r => ({ ...r, band: (r.names_high ?? r.names) - r.names }))
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        <Chip color={NEUTRAL}>Names the town printed</Chip>
        <Chip color="var(--status-warning)" dashed>
          Range — one school&rsquo;s roster printed twice
        </Chip>
      </div>
      <div style={{ height: 230 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" interval={0} minTickGap={2} />
            <YAxis domain={[0, Math.ceil(top / 50) * 50]}
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)" width={44} />
            <Tooltip content={<RosterTip />} cursor={{ fill: 'var(--surface-3)' }} />
            <Bar dataKey="names" stackId="a" fill={NEUTRAL} radius={[0, 0, 0, 0]}
              isAnimationActive={false} />
            <Bar dataKey="band" stackId="a" fill="var(--status-warning)" fillOpacity={0.38}
              radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        School buildings only. Central office and the regional vocational school are
        excluded &mdash; see below for why each.
      </p>
    </Card>
  )
}

/* ------------------------------------------------------------- roles, as small multiples */

export type RoleRow = {
  role: string; total: number; first_fy: number; last_fy: number
  points: { fy: number; names: number; doubled: boolean }[]
}

function RoleTip({ active, payload, label }: {
  active?: boolean
  payload?: { payload: { fy: number; names: number; doubled: boolean } }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-2.5 py-1.5 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{fy(d.fy)} {label} </span>
      <span className="tnum font-bold">{d.names}</span>
      {d.doubled && (
        <p className="mt-1 leading-snug" style={{ color: 'var(--status-warning)' }}>
          one school printed twice
        </p>
      )}
    </div>
  )
}


/** One tiny chart per role, all on the same scale within a row of the grid.
 *
 *  Small multiples rather than a sixteen-series line chart: colour cannot carry sixteen
 *  identities, and a legend of sixteen is a lookup table. Each panel is titled, so nothing
 *  depends on colour at all. */
export function RoleGrid({ rows, format }: { rows: RoleRow[]; format: (s: string) => string }) {
  const top = Math.max(...rows.flatMap(r => r.points.map(p => p.names)))
  return (
    <div className="grid gap-2.5 mt-4"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))' }}>
      {rows.map(r => {
        const first = r.points[0], last = r.points[r.points.length - 1]
        return (
          <div key={r.role} className="card p-3">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[13px] font-bold">{format(r.role)}</span>
              <span className="text-[12px] tnum" style={{ color: 'var(--text-secondary)' }}>
                {first.names} → {last.names}
              </span>
            </div>
            <div style={{ height: 52 }} className="mt-1.5">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={r.points} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}
                  barCategoryGap="12%">
                  <YAxis domain={[0, top]} hide />
                  <XAxis dataKey="fy" hide />
                  <Tooltip cursor={{ fill: 'var(--surface-3)' }}
                    content={<RoleTip label={format(r.role)} />} />
                  <Bar dataKey="names" isAnimationActive={false} radius={[2, 2, 0, 0]}>
                    {r.points.map(p => (
                      <Cell key={p.fy}
                        fill={p.doubled ? 'var(--status-warning)' : COOL}
                        fillOpacity={p.doubled ? 0.5 : 1} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
              {fy(r.points[0].fy)}&ndash;{fy(last.fy)} &middot; {r.total} names in all
            </p>
          </div>
        )
      })}
    </div>
  )
}

/* --------------------------------------------------------- one series against enrolment */

export type StatePoint = {
  fy: number; teacher_fte: number; para_fte: number
  pupils_in_district: number; teachers_per_100: number; paras_per_100: number
}

type EnrolSeries = readonly { key: keyof StatePoint; label: string; hue: string }[]

function EnrolTip({ active, label, rows, series }: {
  active?: boolean; label?: number; rows: StatePoint[]; series: EnrolSeries
}) {
  if (!active || label === undefined) return null
  const raw = rows.find(r => r.fy === label)
  const base = rows[0]
  if (!raw) return null
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {fy(label)}
      </p>
      {series.map(s => (
        <p key={String(s.key)} className="flex justify-between gap-5">
          <span style={{ color: s.hue }}>{s.label}</span>
          <span className="tnum font-semibold">
            {num(raw[s.key], 1)} &middot; {Math.round(100 * raw[s.key] / base[s.key])}
          </span>
        </p>
      ))}
    </div>
  )
}


/** Staff FTE and enrolment, both indexed to the first year on ONE axis.
 *
 *  This is the chart a dual axis would ruin. Teachers are around 105 and pupils around
 *  1,570; drawn on their own scales, any relationship at all can be produced by choosing
 *  the two ranges. Indexed, the reader sees what actually happened to each. */
export function StaffAgainstEnrolment({ rows }: { rows: StatePoint[] }) {
  const base = rows[0]
  const SERIES: EnrolSeries = [
    { key: 'para_fte', label: 'Paraprofessional FTE', hue: SUBJECT },
    { key: 'teacher_fte', label: 'Teacher FTE', hue: COOL },
    { key: 'pupils_in_district', label: 'In-district pupils', hue: NEUTRAL },
  ]
  const data = rows.map(r => {
    const row: Record<string, number> = { fy: r.fy }
    for (const s of SERIES) row[s.key] = 100 * r[s.key] / base[s.key]
    return row
  })
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        {SERIES.map(s => <Chip key={String(s.key)} color={s.hue}>{s.label}</Chip>)}
      </div>
      <div style={{ height: 270 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 10, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" minTickGap={14} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)"
              width={44} />
            <ReferenceLine y={100} stroke="var(--axis)" strokeDasharray="3 3" />
            <Tooltip cursor={{ stroke: 'var(--axis)' }}
              content={<EnrolTip rows={rows} series={SERIES} />} />
            {SERIES.map(s => (
              <Line key={String(s.key)} type="monotone" dataKey={s.key} dot={false} stroke={s.hue}
                strokeWidth={s.key === 'pupils_in_district' ? 1.5 : 2.5}
                strokeDasharray={s.key === 'pupils_in_district' ? '4 3' : undefined}
                isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        All three set to 100 in {fy(base.fy)}. One axis on purpose &mdash; two scales would
        let the picture be chosen rather than read.
      </p>
    </Card>
  )
}

export { Legend }
