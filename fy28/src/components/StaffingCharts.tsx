import { useState } from 'react'
import {
  BarChart, Bar, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceArea, ReferenceLine, ResponsiveContainer,
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

/* --------------------------------------------------------- one series against enrollment */

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


/** Staff FTE and enrollment, both indexed to the first year on ONE axis.
 *
 *  This is the chart a dual axis would ruin. Teachers are around 105 and pupils around
 *  1,570; drawn on their own scales, any relationship at all can be produced by choosing
 *  the two ranges. Indexed, the reader sees what actually happened to each. */
export function StaffAgainstEnrollment({ rows }: { rows: StatePoint[] }) {
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

/** One tooltip shape for the charts added below, because recharts' own `formatter` prop
 *  is typed against `ValueType | undefined` and every call site would otherwise carry a
 *  cast. `rows` is looked up by the category the axis is keyed on, so the tooltip reads
 *  the SOURCE row rather than the rendered datum. */
function PlainTip<T extends { }>({ active, payload, title, lines }: {
  active?: boolean
  payload?: { payload: T }[]
  title: (d: T) => string
  lines: (d: T) => { label: string; value: string; hue?: string }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs max-w-[17rem]"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
        {title(d)}
      </p>
      {lines(d).map(l => (
        <p key={l.label} className="flex justify-between gap-5">
          <span style={{ color: l.hue ?? 'var(--text-secondary)' }}>{l.label}</span>
          <span className="tnum font-semibold">{l.value}</span>
        </p>
      ))}
    </div>
  )
}

/* ============================================================ trends over time
 *
 *  ADDED because "did staffing go up" has no answer that is not a window, and the page
 *  used to pick three windows for the reader. It now hands over the control: the reader
 *  moves the two endpoints and the chart says what the change is between them. That is
 *  the whole finding made operable rather than asserted.
 *
 *  THE SPAN IS ON EVERY CHART. Rule 7b: three years is a trend in this town, because the
 *  boards here will not look two years forward — but a reader must never be able to
 *  mistake three years for fifteen, so every one of these prints its own first and last
 *  year in the frame.
 */

export type DistrictPoint = {
  fy: number; fte: number; students: number | null; high_needs: number | null
  swd: number | null; el: number | null
  per_100_students: number | null; per_100_high_needs: number | null
}

export type NamedWindow = {
  key: string; label: string; first_fy: number; last_fy: number; why: string
}

function WindowTip({ active, label, rows }: {
  active?: boolean; label?: number; rows: DistrictPoint[]
}) {
  if (!active || label === undefined) return null
  const r = rows.find(q => q.fy === label)
  if (!r) return null
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>{fy(r.fy)}</p>
      <p className="flex justify-between gap-5">
        <span style={{ color: SUBJECT }}>Teacher FTE</span>
        <span className="tnum font-semibold">{num(r.fte, 1)}</span>
      </p>
      {r.students !== null && (
        <p className="flex justify-between gap-5">
          <span style={{ color: NEUTRAL }}>Pupils</span>
          <span className="tnum font-semibold">{r.students.toLocaleString()}</span>
        </p>
      )}
      {r.per_100_students !== null && (
        <p className="flex justify-between gap-5">
          <span style={{ color: NEUTRAL }}>Per 100 pupils</span>
          <span className="tnum font-semibold">{num(r.per_100_students, 2)}</span>
        </p>
      )}
    </div>
  )
}

/** The teacher FTE series, with the window as a CONTROL rather than an editorial choice.
 *
 *  Two selects and three presets. Selects rather than a drag handle on purpose: a drag
 *  target on a chart is a 4px hit area on a phone, and the question here is arithmetic
 *  between two named years rather than a gesture. */
export function WindowedSeries({ rows, windows }: {
  rows: DistrictPoint[]; windows: NamedWindow[]
}) {
  const years = rows.map(r => r.fy)
  const preset = windows[0]
  const [lo, setLo] = useState(preset.first_fy)
  const [hi, setHi] = useState(preset.last_fy)
  const a = rows.find(r => r.fy === lo), b = rows.find(r => r.fy === hi)
  const span = rows.filter(r => r.fy >= Math.min(lo, hi) && r.fy <= Math.max(lo, hi))
  const change = a && b ? b.fte - a.fte : 0
  const up = span.reduce((n, r, i) => (i && r.fte > span[i - 1].fte ? n + 1 : n), 0)
  const matched = windows.find(w => w.first_fy === lo && w.last_fy === hi)
  const sel = 'text-[13px] rounded-[8px] border px-2 min-h-[44px] tnum'
  const selStyle = { borderColor: 'var(--grid)', background: 'var(--surface-1)' }
  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <label className="text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
          From{' '}
          <select className={sel} style={selStyle} value={lo}
            onChange={e => setLo(Number(e.target.value))}>
            {years.map(y => <option key={y} value={y}>{fy(y)}</option>)}
          </select>
        </label>
        <label className="text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
          to{' '}
          <select className={sel} style={selStyle} value={hi}
            onChange={e => setHi(Number(e.target.value))}>
            {years.map(y => <option key={y} value={y}>{fy(y)}</option>)}
          </select>
        </label>
        <span className="text-[15px] font-bold tnum ml-1"
          style={{ color: change > 0 ? 'var(--series-revenue)' : change < 0 ? 'var(--series-cost)' : 'var(--text-muted)' }}>
          {change > 0 ? '+' : change < 0 ? '−' : ''}{Math.abs(change).toFixed(1)} FTE
        </span>
      </div>
      <div className="flex flex-wrap gap-2 mb-3" role="group" aria-label="Named windows">
        {windows.map(w => (
          <button key={w.key} title={w.why}
            onClick={() => { setLo(w.first_fy); setHi(w.last_fy) }}
            aria-pressed={matched?.key === w.key}
            className="px-3 min-h-[44px] rounded-[10px] text-[12.5px] font-semibold border"
            style={{
              borderColor: matched?.key === w.key ? 'var(--series-cost)' : 'var(--grid)',
              background: matched?.key === w.key ? 'var(--surface-3)' : 'transparent',
              color: matched?.key === w.key ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}>
            {w.label}
          </button>
        ))}
      </div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 6, right: 10, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" minTickGap={14} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)"
              width={44} domain={['dataMin - 4', 'dataMax + 4']} />
            <ReferenceArea x1={Math.min(lo, hi)} x2={Math.max(lo, hi)}
              fill="var(--series-cost)" fillOpacity={0.09} />
            <Tooltip cursor={{ stroke: 'var(--axis)' }} content={<WindowTip rows={rows} />} />
            <Line type="monotone" dataKey="fte" dot={{ r: 2.5 }} stroke={SUBJECT}
              strokeWidth={2.5} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        Every year the state has published: {fy(rows[0].fy)}&ndash;{fy(rows[rows.length - 1].fy)}.
        Inside the shaded window {up} of {Math.max(span.length - 1, 0)} year-steps rise.
        {matched ? ` This window is ${matched.why}.` : ' This window is one you chose.'}
      </p>
    </Card>
  )
}

/* ------------------------------------------------------------------ by school */

export type SchoolRow = {
  org_code: string; name: string; grades: string; open_now: boolean
  first_fy: number; last_fy: number
  points: { fy: number; fte: number; students: number | null; per_100: number | null }[]
  since_era: { first_fy: number; last_fy: number; first: number; last: number
    change: number; pct: number | null; up: number; steps: number } | null
}

/** One panel per school, on ONE shared vertical scale, from the reconfiguration onward.
 *
 *  Shared scale because the question is which building carries the district's movement,
 *  and per-panel scales would make a school of 18 FTE and a school of 45 look alike. */
export function SchoolPanels({ rows, from }: { rows: SchoolRow[]; from: number }) {
  const shown = rows.map(r => ({ ...r, points: r.points.filter(p => p.fy >= from) }))
    .filter(r => r.points.length >= 2)
  const top = Math.max(...shown.flatMap(r => r.points.map(p => p.fte)))
  return (
    <div className="grid gap-2.5 mt-4"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))' }}>
      {shown.map(r => {
        const first = r.points[0], last = r.points[r.points.length - 1]
        const d = last.fte - first.fte
        return (
          <div key={r.org_code} className="card p-3">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[13px] font-bold leading-tight">{r.name}</span>
              <span className="text-[12.5px] tnum font-bold"
                style={{ color: d >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)' }}>
                {d > 0 ? '+' : d < 0 ? '−' : ''}{Math.abs(d).toFixed(1)}
              </span>
            </div>
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              grades {r.grades || '—'} &middot; {fy(first.fy)}&ndash;{fy(last.fy)}
            </p>
            <div style={{ height: 74 }} className="mt-1.5">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={r.points} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <YAxis domain={[0, top]} hide />
                  <XAxis dataKey="fy" hide />
                  <Tooltip cursor={{ stroke: 'var(--axis)' }} content={
                    <PlainTip<SchoolRow['points'][number]>
                      title={d => `${r.name} · ${fy(d.fy)}`}
                      lines={d => [
                        { label: 'Teacher FTE', value: d.fte.toFixed(1), hue: COOL },
                        ...(d.students !== null
                          ? [{ label: 'Pupils', value: d.students.toLocaleString() }] : []),
                      ]} />} />
                  <Line type="monotone" dataKey="fte" dot={false} stroke={COOL}
                    strokeWidth={2} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
              {first.fte.toFixed(1)} → {last.fte.toFixed(1)} teacher FTE
              {last.per_100 !== null && <> &middot; {last.per_100.toFixed(2)} per 100 pupils</>}
            </p>
          </div>
        )
      })}
    </div>
  )
}

/* --------------------------------------------------- which subject moved, and by how much */

export type SubjectMove = {
  subject: string; first: number; last: number; change: number; pct: number | null
}

/** Signed movement in one diverging bar chart. A pie cannot draw a negative and two
 *  stacked charts hide the thing that matters: the net is small because the arms are
 *  large and cancel. */
export function SubjectMovement({ rows, first_fy, last_fy }: {
  rows: SubjectMove[]; first_fy: number; last_fy: number
}) {
  const shown = rows.filter(r => Math.abs(r.change) >= 0.05)
  return (
    <Card>
      <div style={{ height: Math.max(200, shown.length * 22 + 30) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={shown} layout="vertical"
            margin={{ top: 4, right: 16, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" />
            <YAxis type="category" dataKey="subject" width={150}
              tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} stroke="var(--axis)" />
            <ReferenceLine x={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={
              <PlainTip title={(d: SubjectMove) => d.subject}
                lines={(d: SubjectMove) => [
                  { label: fy(first_fy), value: d.first.toFixed(1) },
                  { label: fy(last_fy), value: d.last.toFixed(1) },
                  { label: 'Change',
                    value: `${d.change > 0 ? '+' : d.change < 0 ? '−' : ''}` +
                      `${Math.abs(d.change).toFixed(1)} FTE`,
                    hue: d.change >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)' },
                ]} />} />
            <Bar dataKey="change" isAnimationActive={false} radius={[2, 2, 2, 2]}>
              {shown.map(r => (
                <Cell key={r.subject}
                  fill={r.change >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        Change in teacher FTE, {fy(first_fy)} to {fy(last_fy)}. Subjects moving less than
        0.05 FTE are left out of the drawing and are in the table.
      </p>
    </Card>
  )
}

/* ------------------------------------------------- headcount beside FTE, never blurred */

export type HeadFte = {
  fy: number; teacher_headcount: number; teacher_fte: number; teacher_share: number
  para_headcount: number; para_fte: number; para_share: number
}

/** People and posts, side by side, on ONE axis because they are the same unit of nothing.
 *
 *  Both are counts of staff, so a shared axis is honest here in a way it would not be for
 *  dollars against FTE. The point of the chart is the GAP, which only reads if the two
 *  bars sit on the same scale. */
export function HeadcountAgainstFte({ rows }: { rows: HeadFte[] }) {
  const data = rows.flatMap(r => ([
    { key: `${r.fy}-t`, label: `${fy(r.fy)} teachers`, people: r.teacher_headcount,
      posts: r.teacher_fte, share: r.teacher_share },
    { key: `${r.fy}-p`, label: `${fy(r.fy)} paras`, people: r.para_headcount,
      posts: r.para_fte, share: r.para_share },
  ]))
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        <Chip color={SUBJECT}>People the state counted</Chip>
        <Chip color={COOL}>Full-time equivalent posts</Chip>
      </div>
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 6, right: 10, left: -14, bottom: 0 }}
            barCategoryGap="22%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 10.5, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" interval={0} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)"
              width={44} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={
              <PlainTip<typeof data[number]>
                title={d => d.label}
                lines={d => [
                  { label: 'People', value: d.people.toFixed(0), hue: SUBJECT },
                  { label: 'FTE posts', value: d.posts.toFixed(1), hue: COOL },
                  { label: 'Share of a post each', value: d.share.toFixed(2) },
                ]} />} />
            <Bar dataKey="people" fill={SUBJECT} isAnimationActive={false} radius={[2, 2, 0, 0]} />
            <Bar dataKey="posts" fill={COOL} isAnimationActive={false} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        {fy(rows[0].fy)}&ndash;{fy(rows[rows.length - 1].fy)}, the only years the state
        publishes a headcount. Two DESE files; the gap between the pair is how much of a
        post the average member of that group holds.
      </p>
    </Card>
  )
}

/* ---------------------------------- the paraprofessional count, split two ways by DESE */

export type ParaSplitPoint = {
  fy: number; all_programmes: number; special_education: number; implied: number
  swd: number | null
}

export function ParaSplit({ rows }: { rows: ParaSplitPoint[] }) {
  const SERIES = [
    { key: 'all_programmes', label: 'All programmes', hue: SUBJECT },
    { key: 'special_education', label: 'Coded to special education', hue: COOL },
    { key: 'implied', label: 'The difference between them', hue: NEUTRAL },
  ] as const
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        {SERIES.map(s => (
          <Chip key={s.key} color={s.hue} dashed={s.key === 'implied'}>{s.label}</Chip>
        ))}
      </div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 6, right: 10, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} stroke="var(--axis)"
              width={44} />
            <Tooltip cursor={{ stroke: 'var(--axis)' }} content={
              <PlainTip title={(d: ParaSplitPoint) => fy(d.fy)}
                lines={(d: ParaSplitPoint) => [
                  { label: 'All programmes', value: `${d.all_programmes.toFixed(1)} FTE`,
                    hue: SUBJECT },
                  { label: 'Special education',
                    value: `${d.special_education.toFixed(1)} FTE`, hue: COOL },
                  { label: 'The difference', value: `${d.implied.toFixed(1)} FTE` },
                  ...(d.swd !== null
                    ? [{ label: 'Children on a plan', value: String(d.swd) }] : []),
                ]} />} />
            {SERIES.map(s => (
              <Line key={s.key} type="monotone" dataKey={s.key} dot={{ r: 2.5 }}
                stroke={s.hue} strokeWidth={s.key === 'implied' ? 1.5 : 2.5}
                strokeDasharray={s.key === 'implied' ? '4 3' : undefined}
                isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        {fy(rows[0].fy)}&ndash;{fy(rows[rows.length - 1].fy)}. Two DESE files, one axis,
        both in full-time equivalents. The dotted line is one subtracted from the other and
        is DERIVED &mdash; it is not a figure either file prints.
      </p>
    </Card>
  )
}

/* ------------------------------------------------ headcount per 100 pupils, by district */

export type PeerHead = {
  lea: string; district: string; job_class: string; headcount: number
  students: number; per_100: number | null; is_lunenburg: boolean
}

export function PeerHeadcount({ rows, jobClass, fyOf }: {
  rows: PeerHead[]; jobClass: string; fyOf: number
}) {
  const shown = rows.filter(r => r.job_class === jobClass && r.per_100 !== null)
    .sort((a, b) => b.per_100! - a.per_100!)
  return (
    <Card>
      <p className="text-[13px] font-bold mb-1">{jobClass}</p>
      <div style={{ height: Math.max(150, shown.length * 26 + 26) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={shown} layout="vertical"
            margin={{ top: 4, right: 16, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              stroke="var(--axis)" />
            <YAxis type="category" dataKey="district" width={130}
              tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={
              <PlainTip title={(d: PeerHead) => d.district}
                lines={(d: PeerHead) => [
                  { label: 'Per 100 pupils',
                    value: d.per_100 === null ? '—' : d.per_100.toFixed(2), hue: SUBJECT },
                  { label: 'People', value: d.headcount.toFixed(0) },
                  { label: 'Pupils', value: d.students.toLocaleString() },
                ]} />} />
            <Bar dataKey="per_100" isAnimationActive={false} radius={[0, 2, 2, 0]}>
              {shown.map(r => (
                <Cell key={r.lea} fill={r.is_lunenburg ? SUBJECT : PEER}
                  fillOpacity={r.is_lunenburg ? 1 : 0.45} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
        {fy(fyOf)} &middot; headcount, not FTE &middot; {shown.length} districts, which is
        not the same comparison group as the rest of this page.
      </p>
    </Card>
  )
}
