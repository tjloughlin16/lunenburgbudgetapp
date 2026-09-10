import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceArea,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

/** The charts for /which-grades-students-leave. Every series arrives from
 *  /data/attrition.json, written by scripts/build_attrition.py — nothing here
 *  computes a figure and nothing here has one typed into it (rule 2).
 *
 *  EVERY VALUE DRAWN IS A RATE, and that governs the whole file. A rate has no additive
 *  meaning, so nothing here stacks, nothing here totals, and no chart puts two grades in
 *  one bar. Where a number of children is drawn it is on its own chart, its own axis and
 *  its own caption saying the count is IMPLIED rather than published.
 *
 *  ONE GRADE IS THREE TIMES THE OTHERS, which is a drawing problem before it is a
 *  finding: on a shared axis the other eleven grades flatten into a rule. They are drawn
 *  on that axis anyway, because the flattening IS the finding, and the table twin carries
 *  the eleven values a reader cannot read off the bars.
 *
 *  THE ERAS ARE SHADED, NOT ANNOTATED. Lunenburg reorganised its buildings twice inside
 *  this series. A DISTRICT grade series is immune to that — a grade is a grade wherever
 *  the town houses it — and the bands are drawn anyway, because the page's own
 *  school-level chart shows what happens to a series that is not immune, and the two have
 *  to be read against the same boundaries.
 *
 *  COLOUR HAS ONE JOB: WHICH SERIES. Nothing here is coloured good or bad.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is one they cannot
 *  check. */

export const RATE = 'var(--series-cost)'
export const OTHER = 'var(--text-muted)'
export const BAND = 'var(--surface-3)'
export const COVID = 'var(--status-warning)'
export const KIDS = 'var(--fund-school)'

export const syShort = (n: number) => `SY${String(n).slice(2)}`
export const syLong = (n: number) => `SY${n}`
export const fyLong = (n: number) => `FY${n}`
export const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`
export const n0 = (n: number) => Math.round(n).toLocaleString()
export const n1 = (n: number) => n.toFixed(1)
export const pts = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)} points`

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }

export type GradeStat = {
  grade: string; mean: number; median: number; min: number; min_sy: number
  max: number; max_sy: number; years: number; times_highest: number
}

export type YearPoint = {
  sy: number; cohort_fy: number; rate: number
  cohort: number | null; implied: number | null
}

export type Band = {
  first_sy: number; last_sy: number; span: string; covid: boolean
  first_asserted: boolean; last_asserted: boolean
  outlier_mean: number; all_mean: number; years_in_file: number
}

export type GroupRow = {
  grp: string; published_years: number; years: number; broken: boolean
  mean?: number; min?: number; max?: number; gap_points?: number
  all_mean: number | null
  series: { sy: number; cohort_fy: number; rate: number | null; all: number | null }[]
}

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 190 }}>{children}</div>
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

/** Every grade, averaged over the whole file.
 *
 *  ONE BAR IS COLOURED DIFFERENTLY AND IT IS NOT AN EDITORIAL CHOICE: the page passes the
 *  grade its own generator DERIVED as the highest in every measured year. If the data
 *  ever stops having one, the generator stops publishing one and nothing here is
 *  highlighted. */
export function GradeProfile({ rows, outlier }: { rows: GradeStat[]; outlier: string }) {
  return (
    <div style={{ width: '100%', height: 300 }} className="mt-5 avoid-break">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="grade" tick={AXIS} stroke="var(--axis)" />
          <YAxis tick={AXIS} stroke="var(--axis)"
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <Tooltip cursor={{ fill: 'var(--surface-3)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as GradeStat
              return (
                <Box>
                  <p className="font-bold">Grade {r.grade}</p>
                  <p>{pct1(r.mean)} on average, over {r.years} years</p>
                  <p style={{ color: 'var(--text-muted)' }}>
                    {pct1(r.min)} in {syLong(r.min_sy)} to {pct1(r.max)} in{' '}
                    {syLong(r.max_sy)}
                  </p>
                </Box>
              )
            }} />
          <Bar dataKey="mean" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {rows.map(r => (
              <Cell key={r.grade} fill={r.grade === outlier ? RATE : OTHER} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The outlier grade, year by year, with the eras behind it.
 *
 *  THE BANDS ARE ALTERNATED RATHER THAN LABELLED GOOD OR BAD, and the one we ASSERTED --
 *  the pandemic -- is drawn in a different ink from the ones read off DESE's grade spans,
 *  so a reader can take it or leave it separately. */
export function OverTime({ points, bands, mean }: {
  points: YearPoint[]; bands: Band[]; mean: number
}) {
  const data = points.map(p => ({ ...p, x: syShort(p.sy) }))
  return (
    <div style={{ width: '100%', height: 320 }} className="mt-5 avoid-break">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          {bands.map((b, i) => (
            <ReferenceArea key={b.first_sy} x1={syShort(b.first_sy)}
              x2={syShort(b.last_sy)} ifOverflow="extendDomain"
              fill={b.covid ? COVID : BAND}
              fillOpacity={b.covid ? 0.13 : i % 2 ? 0.85 : 0} />
          ))}
          <XAxis dataKey="x" tick={AXIS} stroke="var(--axis)" />
          <YAxis tick={AXIS} stroke="var(--axis)" domain={[0, 'auto']}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <ReferenceLine y={mean} stroke="var(--axis)" strokeDasharray="4 3" />
          <Tooltip cursor={{ fill: 'var(--surface-3)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as YearPoint
              return (
                <Box>
                  <p className="font-bold">{syLong(r.sy)}</p>
                  <p>{pct1(r.rate)} of the {fyLong(r.cohort_fy)} eighth grade</p>
                  {r.cohort !== null && r.implied !== null ? (
                    <p style={{ color: 'var(--text-muted)' }}>
                      {n0(r.cohort)} children, implying about {n0(r.implied)}
                    </p>
                  ) : null}
                </Box>
              )
            }} />
          <Bar dataKey="rate" fill={RATE} radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Selected populations at the one grade that moves, against All Students.
 *
 *  THE REFERENCE LINE IS THE POINT. A group's rate on its own says nothing a reader can
 *  use; the same rate beside the town's own average is the whole finding. And the bars
 *  are horizontal because the labels are phrases rather than numbers. */
export function GroupBars({ rows, reference }: { rows: GroupRow[]; reference: number }) {
  const data = rows.filter(r => r.mean !== undefined)
    .map(r => ({ ...r, label: r.grp }))
  return (
    <div style={{ width: '100%', height: 40 * data.length + 60 }}
      className="mt-5 avoid-break">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical"
          margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tick={AXIS} stroke="var(--axis)"
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <YAxis type="category" dataKey="label" width={168} tick={AXIS}
            stroke="var(--axis)" />
          <ReferenceLine x={reference} stroke="var(--axis)" strokeDasharray="4 3" />
          <Tooltip cursor={{ fill: 'var(--surface-3)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as GroupRow
              return (
                <Box>
                  <p className="font-bold">{r.grp}</p>
                  <p>{r.mean === undefined ? '' : pct1(r.mean)} on average,
                    over {r.published_years} published years</p>
                  {r.min !== undefined && r.max !== undefined ? (
                    <p style={{ color: 'var(--text-muted)' }}>
                      {pct1(r.min)} to {pct1(r.max)} between them
                    </p>
                  ) : null}
                </Box>
              )
            }} />
          <Bar dataKey="mean" radius={[0, 2, 2, 0]} isAnimationActive={false}>
            {data.map(r => (
              <Cell key={r.grp} fill={r.broken ? OTHER : RATE} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The churn against the change: implied departures as bars, district enrolment as a
 *  line, on two axes that are deliberately not comparable.
 *
 *  TWO AXES IS USUALLY A MISTAKE AND HERE IT IS THE SUBJECT. The bars are an annual FLOW
 *  and the line is a STOCK; drawing them on one scale would make the flow invisible,
 *  which is exactly the reading this section exists to correct. */
export function Churn({ years, enrolment }: {
  years: { sy: number; cohort_fy: number; cohort: number; rate: number
           implied: number }[]
  enrolment: { fy: number; total: number }[]
}) {
  const by = new Map(enrolment.map(e => [e.fy, e.total]))
  const data = years.map(y => ({ ...y, x: syShort(y.sy), total: by.get(y.sy) ?? null }))
  return (
    <div style={{ width: '100%', height: 300 }} className="mt-5 avoid-break">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="x" tick={AXIS} stroke="var(--axis)" />
          <YAxis yAxisId="left" tick={AXIS} stroke="var(--axis)" />
          <YAxis yAxisId="right" orientation="right" tick={AXIS} stroke="var(--axis)"
            domain={['dataMin - 100', 'dataMax + 100']} />
          <Tooltip cursor={{ fill: 'var(--surface-3)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as { sy: number; implied: number
                                                rate: number; total: number | null }
              return (
                <Box>
                  <p className="font-bold">{syLong(r.sy)}</p>
                  <p>about {n0(r.implied)} children left, implied &mdash;{' '}
                    {pct1(r.rate)} of grades K to 11</p>
                  {r.total === null ? null : (
                    <p style={{ color: 'var(--text-muted)' }}>
                      {n0(r.total)} enrolled that October
                    </p>
                  )}
                </Box>
              )
            }} />
          <Bar yAxisId="left" dataKey="implied" fill={KIDS} radius={[2, 2, 0, 0]}
            isAnimationActive={false} />
          <Line yAxisId="right" type="monotone" dataKey="total" stroke={RATE}
            strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** One school's own published rate, with the years it held a different grade span drawn
 *  in a different fill. This chart exists to be MISREAD on purpose and then corrected in
 *  the sentence under it. */
export function SchoolArtefact({ rows, grade }: {
  rows: { sy: number; cohort_fy: number; all: number; held_outlier_grade: boolean
          span: string }[]
  grade: string
}) {
  const data = rows.map(r => ({ ...r, x: syShort(r.sy) }))
  return (
    <div style={{ width: '100%', height: 260 }} className="mt-5 avoid-break">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="x" tick={AXIS} stroke="var(--axis)" />
          <YAxis tick={AXIS} stroke="var(--axis)"
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
          <Tooltip cursor={{ fill: 'var(--surface-3)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as { sy: number; all: number; span: string
                                                held_outlier_grade: boolean }
              return (
                <Box>
                  <p className="font-bold">{syLong(r.sy)}</p>
                  <p>{pct1(r.all)} across the school</p>
                  <p style={{ color: 'var(--text-muted)' }}>
                    grades {r.span} the year before &mdash;{' '}
                    {r.held_outlier_grade
                      ? `grade ${grade} counted here`
                      : `grade ${grade} not in this building`}
                  </p>
                </Box>
              )
            }} />
          <Bar dataKey="all" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {data.map(r => (
              <Cell key={r.sy} fill={r.held_outlier_grade ? RATE : OTHER} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The key for a two-colour chart, printed after the chart it is a key to (rule 7a). */
export function Legend({ items }: { items: { colour: string; label: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-2 text-[12.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span aria-hidden="true" className="inline-block rounded-sm"
            style={{ width: 12, height: 12, background: i.colour }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}
