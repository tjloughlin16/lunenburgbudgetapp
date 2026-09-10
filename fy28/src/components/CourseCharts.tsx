import {
  Bar, BarChart, CartesianGrid, ComposedChart, LabelList, Line, ReferenceArea,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
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
          <Bar dataKey="other" fill={FULL} fillOpacity={0.55} radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
          <Bar dataKey="comparable" fill={RAN} radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
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
            radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
          <Line yAxisId="r" type="monotone" dataKey="comparableAvg" stroke={FULL}
            strokeWidth={2} dot={{ r: 2.5 }} connectNulls={false}
            isAnimationActive={false} />
          <Line yAxisId="r" type="monotone" dataKey="otherAvg" stroke={FULL}
            strokeWidth={2} strokeDasharray="4 3" dot={{ r: 2.5, fill: 'transparent' }}
            connectNulls={false}
            isAnimationActive={false} />
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
          <Bar dataKey="change" fill={RAN} radius={[2, 2, 2, 2]}
            isAnimationActive={false} />
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
            radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
          <Line yAxisId="r" type="monotone" dataKey="share" stroke={FULL}
            strokeWidth={2} dot={{ r: 2.5 }} connectNulls={false}
            isAnimationActive={false} />
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

/* ------------------------------------------------------------------ THE ERA CHARTS
 *
 * WHY EVERY LONG SERIES ON THIS PAGE IS DRAWN INSIDE ERAS. Lunenburg reorganised its
 * buildings twice inside this file. Thomas C Passios closed after SY2012 and every
 * remaining school moved up one grade band; the new middle-school and high-school
 * building opened in SY2017 and the structure reset. So for four years the high school
 * held grade 8, and a subject an eighth grade all takes — or none of it takes — moves
 * the school's share by twenty points when they arrive and back when they leave, without
 * one thing changing about what a ninth to twelfth grader was offered.
 *
 * Three of the four boundaries are read off DESE's own enrolment-by-grade counts. The
 * fourth is the pandemic, which is a judgement rather than a reading, and it is marked as
 * ours everywhere it appears.
 *
 * THE THREE INSTRUMENTS ARE NEVER COMBINED. Teacher FTE is posts, seats are student
 * places (sections times the average class, not a count of children), and participation
 * is the share of the school taking anything in a subject area. They share a time axis
 * and nothing else — no index, no normalisation, no single score.
 */

export const SUBJ_TONES = ['var(--subj-1)', 'var(--subj-2)', 'var(--subj-3)',
                           'var(--subj-4)', 'var(--subj-5)']
/* A second channel, because colour is never the only one. Five patterns, one per hue,
 * so two series that a protan or deutan reader cannot separate by colour are still two
 * different strokes — and every line carries its own name at its right-hand end. */
export const SUBJ_DASH = ['', '7 3', '2 3', '10 3 2 3', '1 4']

export type Band = {
  first_sy: number; last_sy: number; years: number; span: string
  first_asserted: boolean; last_asserted: boolean; covid: boolean
  schools?: string[]; school_count?: number
}

export type EraPoint = {
  sy: number; participation: number; sections: number; seats: number
  avg: number; fte: number | null; students: number
}

export type EraSubject = {
  subj: string; short: string
  eras: { first_sy: number; last_sy: number; covid: boolean; participation: number
          sections: number; seats: number; avg: number; fte: number | null
          fte_years: number; years: number }[]
  years: EraPoint[]
  has_fte: boolean; peak_era: number; low_era: number
}

/** The eras as shaded bands behind a yearly chart.
 *
 *  The band that is NOT the school's current configuration is drawn darker, because it
 *  is the one a reader must not read across. The pandemic band is drawn at the same
 *  weight as any other and named in the caption instead — it is our boundary, not the
 *  state's, and shading it like a structural break would give it an authority it does
 *  not have. */
export function EraShading({ bands, current }: { bands: Band[]; current: string }) {
  return (
    <>
      {bands.filter(b => b.span !== current).map(b => (
        <ReferenceArea key={b.first_sy} x1={sy(b.first_sy)} x2={sy(b.last_sy)}
          fill={BREAK} fillOpacity={0.85} ifOverflow="extendDomain" />
      ))}
      {/* Every other boundary as a rule rather than a fill. Two adjacent tinted bands
        * read as one band twice as wide, which is what an alternating fill produced
        * here -- SY2017-SY2019 and SY2020-SY2022 merged into a single shaded block
        * spanning six years and two different eras. A rule cannot do that. */}
      {bands.slice(1).filter(b => b.span === current).map(b => (
        <ReferenceLine key={`edge-${b.first_sy}`} x={sy(b.first_sy)}
          stroke="var(--axis)" strokeDasharray="3 3" strokeWidth={1} />
      ))}
    </>
  )
}

const METRICS = {
  participation: {
    label: 'share of the school taking it',
    unit: '% of students',
    fmt: (v: number) => `${(v * 100).toFixed(0)}%`,
    tip: (v: number) => `${(v * 100).toFixed(1)}% of the school took it`,
    domain: [0, 1] as [number, number],
  },
  sections: {
    label: 'classes that ran',
    unit: 'sections',
    fmt: (v: number) => n0(v),
    tip: (v: number) => `${n0(v)} sections ran`,
    domain: [0, 'dataMax + 4'] as [number, string],
  },
  seats: {
    label: 'student places',
    unit: 'seats — sections × average class',
    fmt: (v: number) => n0(v),
    tip: (v: number) => `${n0(v)} student places`,
    domain: [0, 'dataMax + 40'] as [number, string],
  },
  fte: {
    label: 'teachers assigned to it',
    unit: 'full-time-equivalent posts',
    fmt: (v: number) => v.toFixed(1),
    tip: (v: number) => `${v.toFixed(2)} full-time posts`,
    domain: [0, 'dataMax + 1'] as [number, string],
  },
} as const

type MetricKey = keyof typeof METRICS

/** One metric, every selected subject, year by year, with the eras shaded behind.
 *
 *  DIRECT LABELS AND NOT A LEGEND. A legend makes a reader carry five colours across the
 *  page and back; a name at the end of its own line does not, and it is the channel that
 *  survives when the hues do not. */
export function SubjectsOverTime({ subjects, bands, current, metric, height = 300 }: {
  subjects: EraSubject[]; bands: Band[]; current: string
  metric: MetricKey; height?: number
}) {
  const M = METRICS[metric]
  const years = bands.length
    ? Array.from({ length: bands[bands.length - 1].last_sy - bands[0].first_sy + 1 },
      (_, i) => bands[0].first_sy + i)
    : []
  /* END LABELS THAT DO NOT OVERPRINT. Two subjects can finish within a point of each
   * other -- History and Foreign Language both end near 58% -- and two names drawn at
   * the same height become one unreadable word. Each label is placed at its own line's
   * end and then pushed down until it clears the ones already placed. Done in PIXELS,
   * during the same render pass, because the thing that must not collide is the drawn
   * text and not the value behind it. */
  const placed = new Map<string, number>()
  const clear = (key: string, y: number) => {
    const had = placed.get(key)
    if (had !== undefined) return had
    let out = Number.isFinite(y) ? y : 0
    let guard = 0
    while ([...placed.values()].some(p => Math.abs(p - out) < 14) && guard++ < 12) out += 14
    placed.set(key, out)
    return out
  }
  /* A ROUND TOP TO THE AXIS. `dataMax` puts the highest observation on the axis and
   * labels it -- 43 sections, 17 posts -- which reads as a threshold rather than as the
   * top of the data. The scale is rounded up to the next tick instead. */
  const peak = Math.max(...subjects.flatMap(s0 =>
    s0.years.map(x => (x[metric] as number | null) ?? 0)), 0)
  const step = [1, 2, 5, 10, 20, 50, 100, 200, 500].find(v => peak / v <= 5) ?? 500
  const top = Math.ceil(peak / step) * step || 1
  const rows = years.map(y => {
    const row: Record<string, number | string | null> = { label: sy(y), sy: y }
    subjects.forEach(s => {
      const p = s.years.find(x => x.sy === y)
      const v = p ? (p[metric] as number | null) : null
      row[s.short] = v === null || v === undefined ? null : v
    })
    return row
  })
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <EraShading bands={bands} current={current} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false}
            interval="preserveStartEnd" minTickGap={12} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={44}
            domain={metric === 'participation' ? [0, 1] : [0, top]}
            allowDecimals={false}
            ticks={metric === 'participation' ? [0, 0.25, 0.5, 0.75, 1]
              : niceTicks(0, top, [1, 2, 5, 10, 20, 50, 100, 200, 500], 5)}
            tickFormatter={M.fmt} />
          <Tooltip cursor={{ stroke: 'var(--axis)' }} content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null
            const shown = payload.filter(p => p.value !== null && p.value !== undefined)
            if (!shown.length) return null
            return (
              <Box>
                <div className="font-bold">SY20{String(label).slice(2)}</div>
                {shown.map(p => (
                  <div key={String(p.dataKey)} style={{ color: p.color }}>
                    {String(p.dataKey)} — {M.tip(Number(p.value))}
                  </div>
                ))}
              </Box>
            )
          }} />
          {subjects.map((s, i) => (
            <Line key={s.short} type="monotone" dataKey={s.short}
              stroke={SUBJ_TONES[i % SUBJ_TONES.length]}
              strokeDasharray={SUBJ_DASH[i % SUBJ_DASH.length] || undefined}
              strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false}>
              <LabelList dataKey={s.short} position="right" content={(props: {
                index?: number; x?: number | string; y?: number | string
              }) => {
                if (props.index !== rows.length - 1) return null
                const v = rows[rows.length - 1][s.short]
                if (v === null || v === undefined) return null
                return (
                  <text x={Number(props.x) - 2} y={clear(s.short, Number(props.y) - 6)}
                    textAnchor="end" fontSize={10.5}
                    fill={SUBJ_TONES[i % SUBJ_TONES.length]}
                    fontWeight={600}>{s.short}</text>
                )
              }} />
            </Line>
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Chips a reader picks subjects with. The count is capped at the palette, so a sixth
 *  choice replaces the oldest rather than adding a hue nothing validated. */
export function SubjectChips({ all, chosen, onToggle, max }: {
  all: EraSubject[]; chosen: string[]; onToggle: (s: string) => void; max: number
}) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-3">
      {all.map(s => {
        const at = chosen.indexOf(s.short)
        const on = at >= 0
        return (
          <button key={s.short} type="button" onClick={() => onToggle(s.short)}
            aria-pressed={on}
            className="text-[12px] px-2 py-1 rounded-full border transition-colors"
            style={{
              borderColor: on ? SUBJ_TONES[at % SUBJ_TONES.length] : 'var(--grid)',
              color: on ? SUBJ_TONES[at % SUBJ_TONES.length] : 'var(--text-secondary)',
              background: on ? 'var(--surface-2)' : 'transparent',
              fontWeight: on ? 600 : 400,
              opacity: !on && chosen.length >= max ? 0.45 : 1,
            }}>{s.short}</button>
        )
      })}
    </div>
  )
}

/** ONE SUBJECT, THREE INSTRUMENTS, FIVE ERAS — the chart that matches a staffing change
 *  to what happened to students.
 *
 *  Each panel carries the yearly figures as faint dots and the ERA MEAN as a bar across
 *  the years it averages. The mean is what survives one bad year in a file that has
 *  several; the dots are what the mean is a mean of, and a reader who wants to disagree
 *  with the averaging can see every point it used.
 *
 *  Three panels rather than three lines, because posts, seats and a percentage are three
 *  units and putting them on one axis would require an index that hides all three. */
export function ThreeInstruments({ subject, bands, height = 92 }: {
  subject: EraSubject; bands: Band[]; height?: number
}) {
  const panels: { key: 'fte' | 'seats' | 'participation'; title: string; unit: string }[] = [
    { key: 'fte', title: 'Teachers assigned to it', unit: 'full-time-equivalent posts' },
    { key: 'seats', title: 'Student places that ran', unit: 'sections × average class' },
    { key: 'participation', title: 'Share of the school taking it', unit: '% of students' },
  ]
  return (
    <div className="mt-4 avoid-break">
      {panels.map(p => {
        const eras = subject.eras.map(e => ({
          ...e, value: e[p.key] as number | null,
        }))
        const vals = eras.map(e => e.value).filter((v): v is number => v !== null)
        if (!vals.length) {
          return (
            <div key={p.key} className="mt-3">
              <p className="text-[12px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
                {p.title}
              </p>
              <p className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
                DESE files no teacher FTE against this subject area, in any year. The
                other two instruments are below.
              </p>
            </div>
          )
        }
        const top = Math.max(...vals)
        const fmt = p.key === 'participation'
          ? (v: number) => `${(v * 100).toFixed(0)}%`
          : p.key === 'fte' ? (v: number) => v.toFixed(1) : (v: number) => n0(v)
        return (
          <div key={p.key} className="mt-3">
            <p className="text-[12px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
              {p.title} <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
                · {p.unit}</span>
            </p>
            <div className="flex items-end gap-1 mt-1.5" style={{ height }}>
              {eras.map((e, i) => {
                const v = e.value
                const h = v === null || !top ? 0 : Math.max(2, (v / top) * height)
                const other = bands[i] && bands[i].span !== bands[bands.length - 1].span
                /* THE VALUE GOES INSIDE A TALL BAR. Written above it, a bar at the top
                 * of the scale puts its own number on top of the panel's title -- which
                 * is exactly what the tallest bar in every panel does, because the scale
                 * is set by it. */
                const inside = h >= 26
                const label = (
                  <span className="text-[11px] tnum text-center"
                    style={{ color: inside ? 'var(--surface-1)' : 'var(--text-secondary)',
                             fontWeight: inside ? 600 : 400 }}>
                    {v === null ? '—' : fmt(v)}
                  </span>
                )
                return (
                  <div key={e.first_sy} className="flex-1 flex flex-col justify-end"
                    style={{ minWidth: 0 }}>
                    {inside ? null : <span className="mb-0.5">{label}</span>}
                    <div style={{
                      height: h,
                      background: other ? 'var(--text-muted)' : RAN,
                      opacity: other ? 0.5 : 0.9,
                      borderRadius: '2px 2px 0 0',
                      display: 'flex', alignItems: 'flex-start',
                      justifyContent: 'center', paddingTop: 3,
                    }}>{inside ? label : null}</div>
                  </div>
                )
              })}
            </div>
            <div className="flex gap-1">
              {eras.map(e => (
                <div key={e.first_sy} className="flex-1 text-[10px] text-center pt-1"
                  style={{ color: 'var(--text-muted)', minWidth: 0 }}>
                  {String(e.first_sy).slice(2)}–{String(e.last_sy).slice(2)}
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* --------------------------------------------------------------- THE QUADRANT CHART
 *
 * TWO INSTRUMENTS ON TWO AXES, AND A THIRD AS THE DOT ITSELF.
 *
 * Horizontal: the change in teacher FTE — full-time-equivalent posts. Vertical: the
 * change in sections — classes that ran. A subject at (−1.5, +3) lost one and a half
 * posts and gained three classes.
 *
 * The four regions are what the chart is for, because each one is a different thing to
 * have happened and neither instrument alone can tell them apart. A subject that lost
 * staff and lost classes contracted; one that lost staff and gained classes did not.
 *
 * THE THIRD INSTRUMENT IS A TEST AND NOT A DECORATION. "Fewer teachers, more classes" is
 * consistent with the same people spread thinner — but only if the classes got FULLER.
 * So a dot is FILLED where the average class grew and HOLLOW where it shrank, which is a
 * shape rather than a hue and survives any kind of colour vision. Where a subject sits in
 * that region with a hollow dot, the spread-thinner reading is refuted by the school's
 * own third measurement, and the page says so rather than drawing a conclusion the dot
 * already contradicts.
 *
 * NOTHING HERE IS COLOURED GOOD OR BAD. One hue, and the relief is position.
 */
export type QuadRow = {
  subj: string; short: string
  fte_first: number; fte_last: number; fte_change: number
  sections_first: number; sections_last: number; sections_change: number
  avg_first: number; avg_last: number; avg_change: number
  students_first: number; students_last: number
  fuller: boolean; agrees: boolean; same_direction: boolean
  quadrant: string | null; on_the_line: boolean; axis: string | null
  step: number; step_from_sy: number; step_to_sy: number
  step_share: number | null; one_step: boolean
}

/** TICKS A READER RECOGNISES.
 *
 *  Recharts derives its own from the padded domain, and a padded domain is not a round
 *  number: the first draft of this chart printed −2.582, −0.582, 1.418 on an axis
 *  measuring teaching posts, and 20.22, 10.78, 1.78 on one counting classes. A class is
 *  a whole thing and a tenth of a post is the smallest quantity DESE publishes, so the
 *  steps here are chosen from a ladder rather than fitted, and ZERO is always on the axis
 *  because zero is where the quadrant boundary is. */
function niceTicks(min: number, max: number, ladder: number[], want = 6): number[] {
  const step = ladder.find(s2 => (max - min) / s2 <= want) ?? ladder[ladder.length - 1]
  const out: number[] = []
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    out.push(Math.abs(v) < 1e-9 ? 0 : Number(v.toFixed(4)))
  }
  return out.includes(0) ? out : [...out, 0].sort((a, b) => a - b)
}

/** The four corner labels, ON TWO LINES.
 *
 *  One line each is 150px of text, and at 390px the plot is about 330px wide — so the
 *  top-left and top-right labels ran into each other and read as one nonsense phrase.
 *  Two lines halve the width and cost nothing at any size, so this is not a mobile
 *  special case; it is what the label should always have been. Drawn from the
 *  ReferenceArea's own viewBox rather than positioned by hand, so the label follows the
 *  region it names when the domain changes. */
const CORNERS: [[string, string], -1 | 1, -1 | 1][] = [
  [['fewer teachers', 'more classes'], -1, 1],
  [['more teachers', 'more classes'], 1, 1],
  [['fewer teachers', 'fewer classes'], -1, -1],
  [['more teachers', 'fewer classes'], 1, -1],
]

function cornerLabel(lines: [string, string], sx: -1 | 1, sy2: -1 | 1, size: number) {
  return (props: { viewBox?: { x?: number; y?: number; width?: number; height?: number } }) => {
    const v = props.viewBox
    if (!v || v.x === undefined || v.y === undefined) return <g />
    const pad = 5
    const x = sx < 0 ? v.x + pad : v.x + (v.width ?? 0) - pad
    const top = sy2 > 0
    const y = top ? v.y + pad + size : v.y + (v.height ?? 0) - pad - size
    return (
      <text x={x} y={y} textAnchor={sx < 0 ? 'start' : 'end'} fontSize={size}
        fill="var(--text-muted)">
        <tspan x={x}>{lines[0]}</tspan>
        <tspan x={x} dy={size + 2}>{lines[1]}</tspan>
      </text>
    )
  }
}

export function Quadrant({ rows, height = 380, compact = false }: {
  rows: QuadRow[]; height?: number; compact?: boolean
}) {
  const xs = rows.map(r => r.fte_change)
  const ys = rows.map(r => r.sections_change)
  const xPad = Math.max(0.6, (Math.max(...xs) - Math.min(...xs)) * 0.22)
  const yPad = Math.max(2, (Math.max(...ys) - Math.min(...ys)) * 0.18)
  const xd: [number, number] = [Math.min(...xs, 0) - xPad, Math.max(...xs, 0) + xPad]
  const yd: [number, number] = [Math.min(...ys, 0) - yPad, Math.max(...ys, 0) + yPad]
  const filled = rows.filter(r => r.fuller)
  const hollow = rows.filter(r => !r.fuller)
  const xt = niceTicks(xd[0], xd[1], [0.5, 1, 2, 5])
  const yt = niceTicks(yd[0], yd[1], [1, 2, 5, 10, 20, 50])
  /* WHERE A LABEL GOES WHEN TWO DOTS ARE ON TOP OF EACH OTHER. Three subjects sit within
   * a post and a section of each other near the origin, and three names written at the
   * same offset overprint into one unreadable word. Each dot's label is nudged by its
   * rank among the dots it collides with, so they stack rather than overlap — and the
   * exact values are in the table twin, which is what a reader copies from anyway. */
  const order = [...rows].sort((a, b) =>
    a.fte_change - b.fte_change || a.sections_change - b.sections_change)
  const nudge = new Map<string, number>()
  order.forEach((r, i) => {
    const near = order.filter((o, j) => j < i
      && Math.abs(o.fte_change - r.fte_change) < (xd[1] - xd[0]) * 0.10
      && Math.abs(o.sections_change - r.sections_change) < (yd[1] - yd[0]) * 0.07)
    nudge.set(r.subj, near.length * 12)
  })
  const dot = (fill: boolean) => (props: { cx?: number; cy?: number; payload?: QuadRow }) => {
    const { cx, cy, payload } = props
    if (cx === undefined || cy === undefined || !payload) return <g />
    const dy = nudge.get(payload.subj) ?? 0
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill={fill ? RAN : 'var(--surface-1)'}
          stroke={RAN} strokeWidth={1.6} />
        {dy ? <line x1={cx + 6} y1={cy} x2={cx + 8} y2={cy + dy} stroke="var(--grid)"
          strokeWidth={1} /> : null}
        <text x={cx + 9} y={cy + 3.5 + dy} fontSize={compact ? 10 : 11}
          fill="var(--text-secondary)">{payload.short}</text>
      </g>
    )
  }
  return (
    <div style={{ height }} className="mt-4 avoid-break">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 30, right: 18, bottom: 28, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" />
          {CORNERS.map(([lines, sx, sy2]) => (
            <ReferenceArea key={lines.join(sx + ':' + sy2)}
              x1={sx < 0 ? xd[0] : 0} x2={sx < 0 ? 0 : xd[1]}
              y1={sy2 < 0 ? yd[0] : 0} y2={sy2 < 0 ? 0 : yd[1]}
              fill="transparent" stroke="none"
              label={cornerLabel(lines, sx, sy2, compact ? 9.5 : 10.5)} />
          ))}
          <ReferenceLine x={0} stroke="var(--axis)" strokeWidth={1.2} />
          <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1.2} />
          <XAxis type="number" dataKey="fte_change" domain={xd} ticks={xt} tick={AXIS}
            tickLine={false} axisLine={false}
            tickFormatter={(v: number) => (v === 0 ? '0'
              : (v > 0 ? '+' : '−') + n1(Math.abs(v)))}
            label={{ value: 'change in teacher FTE — full-time posts', position: 'bottom',
                     offset: 4, fontSize: 10.5, fill: 'var(--text-muted)' }} />
          <YAxis type="number" dataKey="sections_change" domain={yd} ticks={yt} tick={AXIS}
            tickLine={false} axisLine={false} width={42}
            tickFormatter={(v: number) => signed(v)}
            label={{ value: 'change in sections — classes that ran', position: 'top',
                     offset: 14, fontSize: 10.5, fill: 'var(--text-muted)',
                     style: { textAnchor: 'start' }, dx: -6 }} />
          <ZAxis range={[60, 60]} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as QuadRow
            return (
              <Box>
                <div className="font-bold">{r.subj}</div>
                <div>{n1(r.fte_first)} → {n1(r.fte_last)} teacher FTE</div>
                <div>{n0(r.sections_first)} → {n0(r.sections_last)} sections</div>
                <div>{n1(r.avg_first)} → {n1(r.avg_last)} students to a class</div>
                <div style={{ color: 'var(--text-muted)' }}>
                  {r.quadrant ?? r.axis}
                </div>
              </Box>
            )
          }} />
          <Scatter data={filled} shape={dot(true)} isAnimationActive={false} />
          <Scatter data={hollow} shape={dot(false)} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The key to the quadrant, and it comes AFTER the chart on purpose — a legend read
 *  before a reader has seen a dot is a legend for a map they have not looked at. */
export function QuadrantKey() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3 text-[12px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-flex items-center gap-1.5">
        <svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5"
          fill={RAN} stroke={RAN} strokeWidth="1.6" /></svg>
        classes got fuller
      </span>
      <span className="inline-flex items-center gap-1.5">
        <svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5"
          fill="var(--surface-1)" stroke={RAN} strokeWidth="1.6" /></svg>
        classes got emptier
      </span>
    </div>
  )
}
