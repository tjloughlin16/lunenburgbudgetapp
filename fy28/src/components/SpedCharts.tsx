import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'
import { GENERAL, GRANTS, fy } from './StoppedFundingCharts'

/** The charts for the four special education reports.
 *
 *  EVERY SERIES ARRIVES FROM A JSON FILE written by scripts/build_special_education.py.
 *  Nothing here computes a figure and nothing here has one typed into it (rule 2).
 *
 *  ONE FILE, FOUR REPORTS, AND NO SHARED SCALE BETWEEN THEM. The charts are together
 *  because they share marks and helpers; the DATA never is. There is deliberately no
 *  component in here that takes a student count and a dollar figure at the same time,
 *  because a component that accepts both is an invitation to divide one by the other.
 *
 *  COLOUR IS INHERITED. `GENERAL` and `GRANTS` are the two marks /what-stopped-being-funded
 *  and /when-grants-end already use for exactly this split, on exactly this DESE return.
 *  A third palette for the same two funds would teach a reader that colour means something
 *  local to a page.
 *
 *  THE SPAN IS STATED ON EVERY CHART. Three years is a trend for this audience — a board
 *  that will not project two years out — and that is exactly why the number of years has
 *  to be on the chart rather than inferred from the axis. */

export { TableTwin, fy } from './StoppedFundingCharts'

const IN_DISTRICT = 'var(--series-cost)'
const OUT_DISTRICT = 'var(--fund-school)'
const COUNT = 'var(--series-cost)'
const RATE = 'var(--series-revenue)'

export function Key({ items }: { items: { color: string; label: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}

/** The span, said out loud under every chart. */
export function Span({ from, to, what }: { from: number; to: number; what: string }) {
  return (
    <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
      {to - from + 1} year{to - from ? 's' : ''} &middot; FY{from}&ndash;FY{to} &middot; {what}
    </p>
  )
}

/* =========================================================== 1. how many students */

export type Count = {
  fy: number; swd: number; enrolled: number; in_district: number
  out_of_district: number; share_pct: number
}

function CountTip({ active, payload }: { active?: boolean; payload?: { payload: Count }[] }) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 240 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>In district</span>
        <span className="tnum">{p.in_district}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Out of district</span>
        <span className="tnum">{p.out_of_district}</span>
      </div>
      <div className="flex justify-between gap-4 mt-1 font-semibold">
        <span>On an IEP</span><span className="tnum">{p.swd}</span>
      </div>
      <div className="flex justify-between gap-4 mt-1">
        <span style={{ color: 'var(--text-secondary)' }}>of {p.enrolled} enrolled</span>
        <span className="tnum">{p.share_pct.toFixed(1)}%</span>
      </div>
    </div>
  )
}

/** The published count, split the one way the file itself splits it — and the two parts
 *  sum to the total in every year, which the generator asserts before this renders. */
export function CountBars({ counts }: { counts: Count[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={counts} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="22%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--axis)" width={40} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={<CountTip />} />
            <Bar dataKey="in_district" stackId="c" isAnimationActive={false} fill={IN_DISTRICT} />
            <Bar dataKey="out_of_district" stackId="c" isAnimationActive={false}
              fill={OUT_DISTRICT} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: IN_DISTRICT, label: 'educated in Lunenburg' },
        { color: OUT_DISTRICT, label: 'placed out of district' },
      ]} />
    </div>
  )
}

export type Para = { fy: number; fte: number; swd_base: number; per_100: number }

function ParaTip({ active, payload }: { active?: boolean; payload?: { payload: Para }[] }) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 230 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>FTE the return prints</span>
        <span className="tnum">{p.fte}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>per 100 with disabilities</span>
        <span className="tnum">{p.per_100.toFixed(1)}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>on a base of</span>
        <span className="tnum">{p.swd_base}</span>
      </div>
    </div>
  )
}

/** Two marks that move opposite ways on one frame, because that IS the observation: the
 *  state's paraprofessional FTE for Lunenburg falls while its own denominator does not.
 *  Both are plotted from zero — neither axis is truncated. */
export function ParaFte({ paras }: { paras: Para[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={paras} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
            <YAxis yAxisId="l" domain={[0, 'auto']} tick={{ fontSize: 11 }}
              stroke="var(--axis)" width={40} />
            <YAxis yAxisId="r" orientation="right" domain={[0, 'auto']}
              tick={{ fontSize: 11 }} stroke="var(--axis)" width={44} />
            <Tooltip content={<ParaTip />} />
            <Line yAxisId="l" type="linear" dataKey="fte" stroke={COUNT} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <Line yAxisId="r" type="linear" dataKey="swd_base" stroke={RATE} strokeWidth={2}
              strokeDasharray="4 3" dot={{ r: 2.5 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: COUNT, label: 'special education paraprofessional FTE (left axis)' },
        { color: RATE, label: 'students with disabilities, the return’s own denominator (right axis)' },
      ]} />
    </div>
  )
}

/* ================================================== 2. where the children go instead */

export type Dest = { district: string; students: number }

/** Horizontal bars, because the labels are district names and a name rotated 45 degrees
 *  is a name nobody reads. */
export function Destinations({ rows }: { rows: Dest[] }) {
  const h = Math.max(200, rows.length * 26 + 24)
  return (
    <div className="mt-5">
      <div style={{ height: h }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical"
            margin={{ top: 4, right: 24, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--axis)" />
            <YAxis type="category" dataKey="district" width={210} tick={{ fontSize: 10.5 }}
              stroke="var(--axis)" interval={0} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} />
            <Bar dataKey="students" isAnimationActive={false} fill={OUT_DISTRICT}
              radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[{ color: OUT_DISTRICT, label: 'Lunenburg residents enrolled there' }]} />
    </div>
  )
}

export type NetPoint = { fy: number; out: number; in: number; net: number }

/** Both directions on one frame, never netted into a single mark. The net is in the
 *  table twin as a number, where it can be read rather than eyeballed off a gap. */
export function ChoiceBothWays({ rows }: { rows: NetPoint[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 230 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--axis)" width={40} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} />
            <Bar dataKey="out" name="leaving under school choice" isAnimationActive={false}
              fill={OUT_DISTRICT} radius={[3, 3, 0, 0]} />
            <Bar dataKey="in" name="arriving under school choice" isAnimationActive={false}
              fill={IN_DISTRICT} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: OUT_DISTRICT, label: 'residents leaving under school choice' },
        { color: IN_DISTRICT, label: 'children arriving from other towns' },
      ]} />
    </div>
  )
}

export type RoutePoint = {
  fy: number; monty_tech: number; school_choice: number; charter: number
  other: number; elsewhere: number; in_lunenburg: number
}

const MONTY = 'var(--fund-school)'
const CHOICE = 'var(--series-cost)'
const CHARTER = 'var(--series-revenue)'

/** THE THREE ROUTES, AS THREE LINES ON ONE FRAME — DELIBERATELY NOT STACKED.
 *
 *  A stacked area would draw a single filled band whose height is the sum, and the sum is
 *  the one quantity this page refuses to present as meaningful: Monty Tech is a member-town
 *  assessment, school choice is a family application, charter is a third statute. Stacking
 *  them says "here is the outflow" and the eye reads the envelope, not the parts.
 *
 *  Three lines say the opposite thing, which is the finding: the envelope is almost flat
 *  and the lines inside it cross. */
export function ThreeRoutes({ rows }: { rows: RoutePoint[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--axis)" width={40} />
            <Tooltip cursor={{ stroke: 'var(--grid)' }} />
            <Line type="monotone" dataKey="monty_tech" name="Monty Tech (member town)"
              stroke={MONTY} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="school_choice" name="school choice"
              stroke={CHOICE} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="charter" name="charter schools"
              stroke={CHARTER} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: MONTY, label: 'Montachusett Regional — Lunenburg is a member town' },
        { color: CHOICE, label: 'school choice — a family applies elsewhere' },
        { color: CHARTER, label: 'charter schools — a different statute again' },
      ]} />
    </div>
  )
}

/* ================================================================ 3. what it costs */

export type Spend = {
  fy: number; gen_fund: number; grants: number; total: number
  outside_share_pct: number; ratio: number | null
}

function SpendTip({ active, payload }: { active?: boolean; payload?: { payload: Spend }[] }) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 270 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>General fund — in the budget</span>
        <span className="tnum">{usd(p.gen_fund)}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Other funds — not in it</span>
        <span className="tnum">{usd(p.grants)}</span>
      </div>
      <div className="flex justify-between gap-4 mt-1 font-semibold">
        <span>All funds</span><span className="tnum">{usd(p.total)}</span>
      </div>
    </div>
  )
}

/** The whole argument of the cost report in one frame: the budget line is the lower
 *  segment, and the bar is what was spent. */
export function TuitionByFund({ spend }: { spend: Spend[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={spend} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="16%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={64} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={<SpendTip />} />
            <Bar dataKey="gen_fund" stackId="f" isAnimationActive={false} fill={GENERAL} />
            <Bar dataKey="grants" stackId="f" isAnimationActive={false} fill={GRANTS}
              radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: GENERAL, label: 'general fund — the line in the budget the town votes' },
        { color: GRANTS, label: 'grants and revolving funds — spent, and not in that line' },
      ]} />
    </div>
  )
}

export type Breaker = {
  fy: number; students: number; eligible: number; threshold: number; paid: number
  reimb_tuition: number; reimb_transport: number; paid_share_of_eligible: number
}

function BreakerTip({ active, payload }: {
  active?: boolean; payload?: { payload: Breaker }[]
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 280 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Eligible expenses claimed</span>
        <span className="tnum">{usd(p.eligible)}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Paid to the district</span>
        <span className="tnum">{usd(p.paid)}</span>
      </div>
      <div className="flex justify-between gap-4 mt-1">
        <span style={{ color: 'var(--text-secondary)' }}>for</span>
        <span className="tnum">{p.students} student{p.students === 1 ? '' : 's'}</span>
      </div>
    </div>
  )
}

/** Claimed against paid, side by side. Never one bar with a share on it: the gap between
 *  them is the threshold the state deducts before it reimburses anything, and a single
 *  percentage hides that there is a mechanism rather than a rate. */
export function CircuitBreaker({ rows }: { rows: Breaker[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="14%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={64} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={<BreakerTip />} />
            <Bar dataKey="eligible" isAnimationActive={false} fill={OUT_DISTRICT}
              radius={[3, 3, 0, 0]} />
            <Bar dataKey="paid" isAnimationActive={false} fill={GRANTS}
              radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: OUT_DISTRICT, label: 'eligible expenses the district claimed' },
        { color: GRANTS, label: 'what the state actually paid' },
      ]} />
    </div>
  )
}

/* ============================================ 4. the route into out-of-district */

export type Cohort = {
  fy: number; grade_span: string; start: string; cohort: number
  no_iep: number; included: number; sub_separate: number
  out_of_district: number; unaccounted: number; reconciles: boolean; ood_pct: number
}

function RouteTip({ active, payload }: {
  active?: boolean; payload?: { payload: Record<string, number> }[]
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 300 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>started in an inclusive setting</span>
        <span className="tnum">{p.incl_ood} of {p.incl_cohort}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>started substantially separate</span>
        <span className="tnum">{p.sub_ood} of {p.sub_cohort}</span>
      </div>
      <p className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
        The counts are the figure. A percentage off a base of tens is one child.
      </p>
    </div>
  )
}

/** THE PERCENTAGE NEVER TRAVELS ALONE. A Lunenburg cohort is tens of children — 14.3%
 *  of 28 is four — so the tooltip carries the counts and the table twin carries both. */
export function RouteBars({ k12 }: { k12: Cohort[] }) {
  const years = [...new Set(k12.map(c => c.fy))].sort()
  const rows = years.map(y => {
    const i = k12.find(c => c.fy === y && /Inclusive/.test(c.start))
    const s = k12.find(c => c.fy === y && /Separate/.test(c.start))
    return {
      fy: y,
      incl_pct: i?.ood_pct ?? 0, sub_pct: s?.ood_pct ?? 0,
      incl_ood: i?.out_of_district ?? 0, incl_cohort: i?.cohort ?? 0,
      sub_ood: s?.out_of_district ?? 0, sub_cohort: s?.cohort ?? 0,
    }
  })
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="20%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
            <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={44} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={<RouteTip />} />
            <Bar dataKey="incl_pct" isAnimationActive={false} fill={IN_DISTRICT}
              radius={[3, 3, 0, 0]} />
            <Bar dataKey="sub_pct" isAnimationActive={false} fill={OUT_DISTRICT}
              radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: IN_DISTRICT, label: 'started in an inclusive setting — share now out of district' },
        { color: OUT_DISTRICT, label: 'started substantially separate — share now out of district' },
      ]} />
    </div>
  )
}

export type PlaceCount = {
  fy: number; total: number | null; collaborative: number | null
  day: number | null; residential: number | null
}

/** The town's own count, on its own frame, with a hole where FY2021 is. The gap is drawn
 *  rather than interpolated: that year's annual report does not print the split, and a
 *  line joined across it would assert a shape nobody published. */
export function PlacementCounts({ rows }: { rows: PlaceCount[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 230 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--axis)" width={36} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} />
            <Bar dataKey="collaborative" name="collaborative" stackId="p"
              isAnimationActive={false} fill={GENERAL} />
            <Bar dataKey="day" name="day" stackId="p" isAnimationActive={false}
              fill={OUT_DISTRICT} />
            <Bar dataKey="residential" name="residential" stackId="p"
              isAnimationActive={false} fill={RATE} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: GENERAL, label: 'collaborative' },
        { color: OUT_DISTRICT, label: 'day' },
        { color: RATE, label: 'residential' },
      ]} />
    </div>
  )
}
