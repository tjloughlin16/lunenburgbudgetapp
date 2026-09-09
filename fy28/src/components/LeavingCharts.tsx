import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'
import { Legend, fy, share } from './StateAidCharts'

/** The charts for /if-students-leave. Every figure arrives from /data/if-students-leave.json,
 *  written by scripts/build_if_students_leave.py — nothing here computes a measurement and
 *  nothing here has one typed into it (rule 2). What this file DOES compute is the scenario
 *  itself, from dials the reader sets, off inputs that arrive measured.
 *
 *  COLOUR. The categorical question is which direction a dollar moves, and it has two
 *  answers: money the town loses, and money the town stops spending. So two hues, the
 *  site's warm series colour for what the town loses and the cool one for what it saves,
 *  with recessive ink for anything assumed rather than measured. Identity is never carried
 *  by colour alone — every chart is directly labelled and has a table twin.
 *
 *  THE SENSITIVITY CHART IS THE POINT. A single net figure would be a false precision on
 *  five assumptions. The curve shows the whole range at once and lets the reader see where
 *  their own belief lands, which is the honest shape for a scenario nobody has measured. */

export const LOSS = 'var(--series-revenue)'
export const SAVE = 'var(--series-cost)'
export const MUTED = 'var(--text-muted)'

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const compact = (n: number) =>
  Math.abs(n) >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M`
    : Math.abs(n) >= 1_000 ? `$${Math.round(n / 1_000)}k` : `$${Math.round(n)}`

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-3 text-[12.5px]"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      {children}
    </div>
  )
}

export { fy, share }

/* ------------------------------------------------------------------------ the asymmetry */

/** TWO BARS ON ONE SCALE, opposed: what the town loses against what it stops spending.
 *
 *  This is the page's whole argument in one mark. Two lengths on a common baseline compare
 *  without arithmetic; the reader does not have to hold either number in their head to see
 *  that one is longer. The scale is fixed to the larger of the two so the shorter bar is
 *  never drawn full-width, which is the failure that would make a $0 saving look like a
 *  match for a $390,000 loss. */
export function Asymmetry({ items }: {
  items: { label: React.ReactNode; amount: number; hue: string; note?: React.ReactNode }[]
}) {
  const top = Math.max(...items.map(i => Math.abs(i.amount)), 1)
  return (
    <div className="mt-5 flex flex-col gap-4">
      {items.map((i, k) => (
        <div key={k}>
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <span className="text-[13.5px] font-semibold">{i.label}</span>
            <span className="text-[15px] font-bold tnum whitespace-nowrap"
              style={{ color: i.hue }}>{usd(i.amount)}</span>
          </div>
          <div className="mt-1.5 rounded-[3px]"
            style={{ background: 'var(--surface-3)', height: 18 }}>
            <div className="rounded-[3px]" style={{
              width: `${Math.max(i.amount > 0 ? 0.8 : 0, (Math.abs(i.amount) / top) * 100)}%`,
              height: 18, background: i.hue,
            }} />
          </div>
          {i.note && (
            <p className="text-[11.5px] mt-1.5 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
              {i.note}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------- where they leave from */

export type Grade = {
  grade: string; resident: number; leaving: number; remaining: number; share: number
}

/** Each grade at its real size, with the share leaving drawn inside it rather than beside
 *  it. Inside, because the finding is that the loss is small relative to the grade it comes
 *  out of — and two adjacent bars would invite the eye to compare the losses with each
 *  other instead. Grades are drawn to a common scale so grade 9 being the smallest is
 *  visible, which is the reason it loses the fewest. */
export function PerGrade({ grades }: { grades: Grade[] }) {
  const top = Math.max(...grades.map(g => g.resident), 1)
  return (
    <div className="mt-5">
      <div className="flex flex-col gap-3">
        {grades.map(g => (
          <div key={g.grade}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-semibold">Grade {g.grade}</span>
              <span className="text-[12.5px] tnum whitespace-nowrap"
                style={{ color: 'var(--text-secondary)' }}>
                {g.leaving.toFixed(1)} of {g.resident} leaving &middot; {share(g.share)}
              </span>
            </div>
            <div className="relative mt-1 rounded-[3px] overflow-hidden"
              style={{ background: 'var(--surface-3)', height: 18,
                       width: `${(g.resident / top) * 100}%` }}>
              <div className="absolute inset-0 rounded-[3px]"
                style={{ background: 'var(--axis)', opacity: 0.35 }} />
              <div className="absolute top-0 left-0" style={{
                width: `${g.share * 100}%`, height: 18, background: LOSS,
              }} />
            </div>
          </div>
        ))}
      </div>
      <Legend items={[
        { hue: LOSS, label: 'The share of that grade the scenario has leaving' },
        { hue: 'var(--axis)', label: 'Resident students the town printed for that grade' },
      ]} />
    </div>
  )
}

/* ---------------------------------------------------------- school choice money coming IN */

export type FundYear = {
  fy: number; receipts: number | null; carried: number | null; usable: boolean
  why: string | null
}

/** The receipts line only. The BALANCE is a different quantity — it is what the fund has
 *  saved up, not what arrived that year — and plotting the two together on one axis would
 *  invite exactly the reading this page exists to avoid. A year the extract could not read
 *  is drawn as a break in the line rather than as a zero. */
export function ChoiceIn({ series, cherry }: {
  series: FundYear[]; cherry: { fy: number; amount: number }[]
}) {
  const data = series.map(r => ({
    fy: fy(r.fy), receipts: r.usable ? r.receipts : null,
  }))
  const cherryData = cherry.map(r => ({ fy: fy(r.fy), cherry: r.amount }))
  const merged = [...data, ...cherryData.filter(c => !data.some(d => d.fy === c.fy))]
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <LineChart data={merged} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compact} />
            <Tooltip cursor={{ stroke: 'var(--grid)' }} content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <Box>
                  <div className="font-bold">{label}</div>
                  {payload.map(p => (
                    <div key={String(p.dataKey)} className="tnum">
                      {p.dataKey === 'cherry' ? 'cherry sheet estimate: ' : 'into the fund: '}
                      {usd(Number(p.value))}
                    </div>
                  ))}
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="receipts" stroke={SAVE} strokeWidth={2}
              dot={{ r: 2.5 }} connectNulls={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="cherry" stroke={LOSS} strokeWidth={2}
              strokeDasharray="4 3" dot={{ r: 2.5 }} connectNulls={false}
              isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: SAVE, label: 'Receipts into the town’s School Choice revolving fund — the annual town reports' },
        { hue: LOSS, label: 'The cherry sheet’s School Choice Receiving line — the FY2027 Town Meeting booklet' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------- the flow that already exists, both ways */

export type FlowYear = {
  sy: number; out_choice: number; out_charter: number; in_choice: number
  net_choice: number
}

/** CHILDREN, NOT DOLLARS, and both directions on one axis because they are the same unit
 *  and the reader's question is which is bigger. A dashed reference line marks where the
 *  scenario would put the outward flow, so the modelled number is read against the real
 *  one rather than in isolation — which is the whole reason this chart is here. */
export function Flows({ series, scenarioOut, scenarioLabel }: {
  series: FlowYear[]; scenarioOut: number; scenarioLabel: string
}) {
  const data = series.map(r => ({
    sy: `SY${String(r.sy).slice(2)}`,
    out: r.out_choice, in: r.in_choice, charter: r.out_charter,
  }))
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 270 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 14, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="sy" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false}
              tickFormatter={(v: number) => String(v)} />
            <ReferenceLine y={scenarioOut} stroke={LOSS} strokeDasharray="5 4"
              label={{ value: scenarioLabel, position: 'insideTopRight',
                       fill: 'var(--text-muted)', fontSize: 11 }} />
            <Tooltip cursor={{ stroke: 'var(--grid)' }} content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <Box>
                  <div className="font-bold">{label}</div>
                  {payload.map(p => (
                    <div key={String(p.dataKey)} className="tnum">
                      {p.dataKey === 'out' ? 'leaving under school choice: '
                        : p.dataKey === 'in' ? 'arriving under school choice: '
                          : 'leaving to charter schools: '}
                      {String(p.value)}
                    </div>
                  ))}
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="out" stroke={LOSS} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <Line type="monotone" dataKey="in" stroke={SAVE} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <Line type="monotone" dataKey="charter" stroke="var(--axis)" strokeWidth={1.5}
              strokeDasharray="3 3" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: LOSS, label: 'Lunenburg residents leaving under school choice' },
        { hue: SAVE, label: 'Children arriving in Lunenburg under school choice' },
        { hue: 'var(--axis)', label: 'Lunenburg residents at charter schools — a different programme' },
      ]} />
    </div>
  )
}

/* ------------------------------------ both directions, every programme, and the net of them */

export type BothWaysYear = {
  sy: number; out_all: number; in_all: number; net_all: number
  out_member: number; out_choice: number; out_charter: number; out_other: number
  in_choice: number; in_tuitioned: number; in_foster: number; in_other: number
}

/** THREE LINES, ONE UNIT, AND THE NET DRAWN WITH ITS TWO HALVES.
 *
 *  The net alone is a near-flat line and it is the most misleading thing this data can be
 *  drawn as: it has never once turned positive and it has barely moved, so on its own it
 *  says nothing is happening — while one of the two series that makes it has fallen by
 *  more than two thirds. That is the whole reason all three are on one axis. A reader who
 *  looks at this chart cannot come away with the flat reading, because the divergence is
 *  the shape.
 *
 *  A ZERO RULE, drawn solid, because the net is negative in every year and "has this ever
 *  been positive" is the question a reader brings. The line never touching the rule is the
 *  answer, read off the picture rather than out of a sentence.
 *
 *  MEASURED, NOT MODELLED. Nothing on this chart moves when a dial moves — it is DESE's
 *  count of children, and it carries no scenario reference line for that reason. The
 *  scenario's own chart is Flows(), below, and keeping the two apart is deliberate. */
export function BothWays({ series }: { series: BothWaysYear[] }) {
  const data = series.map(r => ({
    sy: `SY${String(r.sy).slice(2)}`,
    out: r.out_all, in: r.in_all, net: r.net_all,
  }))
  const label: Record<string, string> = {
    out: 'leaving — Lunenburg children at another district: ',
    in: 'arriving — children from another town at Lunenburg: ',
    net: 'net, arriving minus leaving: ',
  }
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 14, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="sy" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false}
              tickFormatter={(v: number) => String(v)} />
            <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1.5}
              label={{ value: 'no net movement', position: 'insideTopLeft',
                       fill: 'var(--text-muted)', fontSize: 11 }} />
            <Tooltip cursor={{ stroke: 'var(--grid)' }} content={({ active, payload, label: l }) => {
              if (!active || !payload?.length) return null
              return (
                <Box>
                  <div className="font-bold">{l}</div>
                  {payload.map(p => (
                    <div key={String(p.dataKey)} className="tnum">
                      {label[String(p.dataKey)]}{String(p.value)}
                    </div>
                  ))}
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="out" stroke={LOSS} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <Line type="monotone" dataKey="in" stroke={SAVE} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <Line type="monotone" dataKey="net" stroke="var(--axis)" strokeWidth={2}
              strokeDasharray="5 4" dot={{ r: 2 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: LOSS, label: 'Leaving — every Lunenburg child enrolled at another district, all programmes' },
        { hue: SAVE, label: 'Arriving — every child from another town enrolled in Lunenburg, all programmes' },
        { hue: 'var(--axis)', label: 'Net — arriving minus leaving. Below the rule is a net loss of children' },
      ]} />
    </div>
  )
}

/* ----------------------------------------- what aid has done, against what enrollment did */

export type AidYear = { fy: number; enrollment: number; aid: number }

/** ONE AXIS, DOLLARS. Foundation enrollment is on the same picture only as a MARK — a dot
 *  on the aid line for a year enrollment fell — because a second axis in different units
 *  invites a reader to compare two slopes that have no common scale, which is precisely
 *  the inference this chart exists to test. The enrollment numbers are in the table twin,
 *  where they can be read rather than eyeballed. */
export function AidHistory({ series, fellYears }: {
  series: AidYear[]; fellYears: number[]
}) {
  const fell = new Set(fellYears)
  const data = series.map(r => ({ ...r, label: `FY${String(r.fy).slice(2)}` }))
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 270 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false}
              interval={3} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compact} />
            <Tooltip cursor={{ stroke: 'var(--grid)' }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const p = payload[0].payload as typeof data[number]
              return (
                <Box>
                  <div className="font-bold">{p.label}</div>
                  <div className="tnum">{usd(p.aid)} of Chapter 70 aid</div>
                  <div className="tnum" style={{ color: 'var(--text-muted)' }}>
                    {p.enrollment.toLocaleString()} foundation pupils
                    {fell.has(p.fy) ? ' — down on the year before' : ''}
                  </div>
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="aid" stroke={SAVE} strokeWidth={2}
              isAnimationActive={false}
              dot={(props: { cx?: number; cy?: number; payload?: AidYear; index?: number }) => {
                const { cx, cy, payload, index } = props
                if (cx == null || cy == null || !payload) {
                  return <g key={`d${index}`} />
                }
                return fell.has(payload.fy)
                  ? <circle key={`d${index}`} cx={cx} cy={cy} r={4} fill={LOSS} />
                  : <circle key={`d${index}`} cx={cx} cy={cy} r={1.8} fill={SAVE} />
              }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: SAVE, label: 'Chapter 70 aid to Lunenburg, as DESE states it' },
        { hue: LOSS, label: 'A year foundation enrollment was lower than the year before' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------------------- the whole range */

export type Curve = { avoidable: number; hold: number; full: number }

/** The net cost to the town across every value of the one input nobody has measured.
 *
 *  Two curves, because the aid question has two ends and the truth is between them: the
 *  lower assumes Chapter 70 does not move, the upper assumes it falls by the whole
 *  foundation reduction. A zero line is drawn explicitly, since the point where a curve
 *  crosses it is the break-even the page names. */
export function Sensitivity({ curve, breakEven }: {
  curve: Curve[]; breakEven: number | null
}) {
  return (
    <div className="mt-5">
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <LineChart data={curve} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="avoidable" tick={AXIS} tickLine={false} axisLine={false}
              tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compact} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            {breakEven != null && breakEven <= 1 && (
              <ReferenceLine x={curve.reduce((a, b) =>
                Math.abs(b.avoidable - breakEven) < Math.abs(a.avoidable - breakEven) ? b : a
              ).avoidable} stroke="var(--status-good)" strokeDasharray="3 3" />
            )}
            <Tooltip cursor={{ stroke: 'var(--grid)' }} content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <Box>
                  <div className="font-bold">
                    {Math.round(Number(label) * 100)}% of the per-pupil appropriation avoided
                  </div>
                  {payload.map(p => (
                    <div key={String(p.dataKey)} className="tnum">
                      {p.dataKey === 'hold' ? 'aid unchanged: ' : 'aid falls in full: '}
                      {usd(Number(p.value))}
                    </div>
                  ))}
                </Box>
              )
            }} />
            <Line type="monotone" dataKey="full" stroke={LOSS} strokeWidth={2} dot={false}
              isAnimationActive={false} />
            <Line type="monotone" dataKey="hold" stroke={SAVE} strokeWidth={2} dot={false}
              isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[
        { hue: LOSS, label: 'Net cost if aid fell by the whole foundation reduction — the original reading' },
        { hue: SAVE, label: 'Net cost at the aid-per-student figure currently on the dial' },
        { hue: 'var(--status-good)', label: 'Where the town breaks even, if it gets there' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------------------------ one dial */

/** A slider with its own basis printed under it. Every control on this page is an
 *  ASSUMPTION and the page would be dishonest if it did not say so beside each one. */
export function Dial({ label, value, setValue, min, max, step, format, tone, basis, note,
                       reset }: {
  label: React.ReactNode
  value: number; setValue: (n: number) => void
  min: number; max: number; step: number
  format: (n: number) => string
  tone: string
  basis: string
  note: React.ReactNode
  reset: number
}) {
  const moved = Math.abs(value - reset) > 1e-9
  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <h3 className="text-[13px] font-bold">{label}</h3>
        <span className="text-[10px] font-bold uppercase tracking-widest shrink-0"
          style={{ color: basis === 'statute' ? 'var(--text-secondary)' : tone }}>
          {basis}
        </span>
      </div>
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-lg font-bold tnum">{format(value)}</span>
        {moved && (
          <button onClick={() => setValue(reset)}
            className="text-[10px] font-semibold underline"
            style={{ color: 'var(--text-secondary)' }}>reset</button>
        )}
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        aria-label={typeof label === 'string' ? label : undefined}
        onChange={e => setValue(Number(e.target.value))} className="w-full" />
      <p className="text-[11.5px] leading-snug mt-2" style={{ color: 'var(--text-muted)' }}>
        {note}
      </p>
    </div>
  )
}
