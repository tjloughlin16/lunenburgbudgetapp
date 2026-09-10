import {
  Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceArea,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

/** The charts for /what-courses-actually-ran. Every series arrives from
 *  /data/course-offerings.json, written by scripts/build_course_offerings.py — nothing
 *  here computes a headline and nothing here has a figure typed into it (rule 2).
 *
 *  THE GRADE-SPAN BREAK IS DRAWN, NOT ONLY WRITTEN, and it is the whole design of this
 *  file. `Lunenburg High` means grades 8-12 for four of the fifteen years in the source
 *  and grades 9-12 for the other eleven, so a single line through all fifteen would draw
 *  a reorganisation as a trend. Every long chart here therefore does two things at once:
 *  it SHADES the years the school held a different grade span, and it splits the series
 *  into separate dataKeys either side of the break, holding `null` outside their own era.
 *  Two keys cannot produce one path — which is the point, because a reader who does
 *  not read the caption still cannot see a trend across the break, and neither can a
 *  future edit accidentally reintroduce one by changing a prop.
 *
 *  TWO QUANTITIES, NEVER BLURRED. `sections` is what RAN; `avg` is how FULL it was. They
 *  move independently — a district can keep a subject and halve its sections, or keep
 *  its sections and pack them — so they are never the same mark and never the same
 *  colour. Where both appear on one chart the sections are bars and the size is a line,
 *  and the caption says which axis is which.
 *
 *  COLOUR HAS ONE JOB: WHICH SERIES. Nothing here is coloured good or bad. A subject
 *  losing sections is drawn in the same hue as one gaining them and the relief is
 *  position on an axis.
 *
 *  THE SPAN IS ON EVERY CHART, in its caption. TJ's rule for this town is that three
 *  years is more forward visibility than its boards currently use, and the way that stays
 *  honest is saying how many years are drawn.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is one they cannot
 *  check. */

export const RAN = 'var(--series-cost)'
export const FULL = 'var(--text-muted)'
export const BREAK = 'var(--surface-3)'

export const sy = (n: number) => `SY${String(n).slice(2)}`
export const syLong = (n: number) => `SY${n}`
export const n0 = (n: number) => Math.round(n).toLocaleString()
export const n1 = (n: number) => n.toFixed(1)
export const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
export const signed = (n: number) => (n > 0 ? `+${n0(n)}` : n < 0 ? `−${n0(-n)}` : '0')

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }

export type Point = {
  sy: number; sections: number; avg: number; students: number
  seats?: number; seats_per_student?: number | null
}

export type Subject = {
  subj: string; points: { sy: number; sections: number; avg: number; students: number }[]
  first_sy: number; last_sy: number
  first: number; last: number; change: number
  first_avg: number; last_avg: number
  first_students: number; last_students: number
  share_of_students: number | null
}

export type Era = { span: string; first_sy: number; last_sy: number }

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 200 }}>{children}</div>
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

export function Caption({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[12.5px] leading-relaxed max-w-2xl mt-2"
      style={{ color: 'var(--text-muted)' }}>{children}</p>
  )
}

/** The eras that are NOT the one this page reads, as shaded bands behind a chart.
 *
 *  A band rather than a line, because the thing being marked is a SPAN of years and not
 *  an instant: the school held different grades for four whole years, and a vertical rule
 *  at each end would read as two events rather than one condition. */
function Breaks({ eras, keep }: { eras: Era[]; keep: string }) {
  return (
    <>
      {eras.filter(e => e.span !== keep).map(e => (
        <ReferenceArea key={e.first_sy} x1={sy(e.first_sy)} x2={sy(e.last_sy)}
          fill={BREAK} fillOpacity={0.85} ifOverflow="extendDomain" />
      ))}
    </>
  )
}

/** Sections that ran, per year, with the years of a different grade span shaded. */
export function SectionsOverTime({ points, eras, keep, height = 260 }: {
  points: Point[]; eras: Era[]; keep: string; height?: number
}) {
  const rows = points.map(p => ({
    label: sy(p.sy), sy: p.sy,
    comparable: eras.some(e => e.span === keep && p.sy >= e.first_sy && p.sy <= e.last_sy)
      ? p.sections : null,
    other: eras.some(e => e.span === keep && p.sy >= e.first_sy && p.sy <= e.last_sy)
      ? null : p.sections,
    avg: p.avg, students: p.students,
  }))
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <Breaks eras={eras} keep={keep} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={44} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as typeof rows[number]
            return (
              <Box>
                <div className="font-bold">{syLong(r.sy)}</div>
                <div>{n0(r.comparable ?? r.other ?? 0)} sections ran</div>
                <div style={{ color: 'var(--text-muted)' }}>
                  {n1(r.avg)} students to a class · {n0(r.students)} students enrolled
                </div>
              </Box>
            )
          }} />
          <Bar dataKey="other" fill={FULL} fillOpacity={0.55} radius={[2, 2, 0, 0]} />
          <Bar dataKey="comparable" fill={RAN} radius={[2, 2, 0, 0]} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The two quantities on one chart: how many classes ran (bars, left) against how full
 *  they were (line, right). The only chart on this page that carries two scales, and it
 *  carries them because the whole point is that they move independently. */
export function RanAgainstFull({ points, eras, keep, height = 280 }: {
  points: Point[]; eras: Era[]; keep: string; height?: number
}) {
  const rows = points.map(p => ({
    label: sy(p.sy), sy: p.sy, sections: p.sections, avg: p.avg, students: p.students,
    comparableAvg: eras.some(e => e.span === keep && p.sy >= e.first_sy
      && p.sy <= e.last_sy) ? p.avg : null,
    otherAvg: eras.some(e => e.span === keep && p.sy >= e.first_sy
      && p.sy <= e.last_sy) ? null : p.avg,
  }))
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <Breaks eras={eras} keep={keep} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} />
          <YAxis yAxisId="l" tick={AXIS} tickLine={false} axisLine={false} width={44} />
          <YAxis yAxisId="r" orientation="right" tick={AXIS} tickLine={false}
            axisLine={false} width={36} domain={[0, 'dataMax + 4']} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as typeof rows[number]
            return (
              <Box>
                <div className="font-bold">{syLong(r.sy)}</div>
                <div>{n0(r.sections)} sections ran</div>
                <div>{n1(r.avg)} students to a class</div>
              </Box>
            )
          }} />
          <Bar yAxisId="l" dataKey="sections" fill={RAN} fillOpacity={0.85}
            radius={[2, 2, 0, 0]} />
          <Line yAxisId="r" type="monotone" dataKey="comparableAvg" stroke={FULL}
            strokeWidth={2} dot={{ r: 2.5 }} connectNulls={false} />
          <Line yAxisId="r" type="monotone" dataKey="otherAvg" stroke={FULL}
            strokeWidth={2} strokeDasharray="4 3" dot={{ r: 2.5, fill: 'transparent' }}
            connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** What each subject did across the window, as a diverging bar.
 *
 *  A diverging bar and not two lists, for the reason /what-sports-cost learned: the net
 *  is small because the arms are large and cancel, and only one chart shows that. Ranked
 *  by the SIZE of the move rather than by the size of the subject, because a subject with
 *  many sections that did not move is not the finding. */
export function SubjectChange({ subjects, height = 380 }: {
  subjects: Subject[]; height?: number
}) {
  const rows = [...subjects]
    .filter(s => s.change !== 0)
    .sort((a, b) => a.change - b.change)
    .map(s => ({ subj: s.subj, change: s.change, first: s.first, last: s.last }))
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tick={AXIS} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="subj" tick={{ ...AXIS, fontSize: 10.5 }}
            tickLine={false} axisLine={false} width={168} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as typeof rows[number]
            return (
              <Box>
                <div className="font-bold">{r.subj}</div>
                <div>{n0(r.first)} sections → {n0(r.last)}</div>
                <div style={{ color: 'var(--text-muted)' }}>{signed(r.change)}</div>
              </Box>
            )
          }} />
          <Bar dataKey="change" fill={RAN} radius={[2, 2, 2, 2]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** One subject's sections beside the share of the school taking it. Used for the one
 *  subject where every instrument points the same way, and for nothing else — a
 *  two-series chart per subject would be twenty charts and no finding. */
export function SubjectDetail({ subject, students, height = 250 }: {
  subject: Subject; students: Point[]; height?: number
}) {
  const byYear = new Map(students.map(p => [p.sy, p]))
  const rows = subject.points.map(p => {
    const school = byYear.get(p.sy)
    return {
      label: sy(p.sy), sy: p.sy, sections: p.sections, avg: p.avg,
      share: school && school.students ? p.students / school.students : null,
      students: p.students,
    }
  })
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} />
          <YAxis yAxisId="l" tick={AXIS} tickLine={false} axisLine={false} width={40} />
          <YAxis yAxisId="r" orientation="right" tick={AXIS} tickLine={false}
            axisLine={false} width={44} domain={[0, 1]}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as typeof rows[number]
            return (
              <Box>
                <div className="font-bold">{syLong(r.sy)}</div>
                <div>{n0(r.sections)} sections · {n1(r.avg)} to a class</div>
                <div style={{ color: 'var(--text-muted)' }}>
                  {n0(r.students)} students took it
                  {r.share === null ? null : ` — ${pct1(r.share)} of the school`}
                </div>
              </Box>
            )
          }} />
          <Bar yAxisId="l" dataKey="sections" fill={RAN} fillOpacity={0.85}
            radius={[2, 2, 0, 0]} />
          <Line yAxisId="r" type="monotone" dataKey="share" stroke={FULL}
            strokeWidth={2} dot={{ r: 2.5 }} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export function Legend({ items }: { items: { tone: string; label: string; dash?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3 text-[12px]"
      style={{ color: 'var(--text-secondary)' }}>
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" style={{
            width: 16, height: i.dash ? 0 : 10, borderTop: i.dash ? `2px dashed ${i.tone}` : undefined,
            background: i.dash ? undefined : i.tone, borderRadius: 2, display: 'inline-block',
          }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}
