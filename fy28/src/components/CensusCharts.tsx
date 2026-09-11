import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, LabelList, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

/* Every Bar here sets `isAnimationActive={false}`. Recharts animates a bar up from zero
 * on mount, and a headless capture takes its picture before the animation finishes --
 * which renders every bar on the page BLANK in exactly the screenshot somebody is
 * reviewing the chart from. It also removes a needless animation on a page of static
 * measurements. */

/** The charts for /lunenburg-by-the-numbers. Every series arrives from
 *  /data/lunenburg-by-the-numbers.json, written by
 *  scripts/build_lunenburg_by_the_numbers.py — nothing here computes a figure and
 *  nothing here has one typed into it (rule 2).
 *
 *  THE MARGIN IS DRAWN, NOT ONLY WRITTEN, AND THAT IS THE DESIGN OF THIS FILE. Every
 *  figure on this page is a five-year SAMPLE estimate: 1,979 residents 65 or over means
 *  somewhere between 1,670 and 2,288, and a bar drawn to 1,979 with nothing else on it
 *  says the first thing while hiding the second. So every estimate here carries a whisker
 *  of its own margin, and a reader who never gets to the caption still cannot read these
 *  bars as counts.
 *
 *  ONE HUE PER CHART, AND NO CHART CARRIES TWO SERIES. Colour has no job here beyond
 *  "this is the data": no age group is good, no income band is bad, and the only mark
 *  that is coloured differently is the bin Lunenburg itself falls in on the statewide
 *  distribution — identity, not rank.
 *
 *  THE COMPARISON CHART IS DRAWN IN MULTIPLES OF ITS OWN MARGIN rather than in its own
 *  units, and that is not decoration either. Fifteen comparisons across two five-year
 *  releases are counted in people, in households, in dollars and in percentage points,
 *  and a single axis cannot carry four units — the alternative is four charts of four
 *  bars, or a dual axis, which is worse than both. Dividing each difference by its own
 *  combined margin makes the axis unitless and makes it the TEST: past 1 and the
 *  difference clears its margin, inside 1 and it is a difference this instrument cannot
 *  see.
 *
 *  Every chart has a table twin. A figure a reader cannot copy out is one they cannot
 *  check. */

export const INK = 'var(--series-cost)'
export const MUTED = 'var(--text-muted)'
export const MARK = 'var(--series-revenue)'

export const n0 = (v: number) => Math.round(v).toLocaleString('en-US')
export const usd0 = (v: number) => '$' + Math.round(v).toLocaleString('en-US')

export type Est = {
  label: string; estimate: number; moe: number
  text: string; estimate_text: string; moe_text: string
}

export type AgeGroup = Est & {
  key: string; share: number; share_moe: number
  share_text: string; share_moe_text: string
}

export type Bin = {
  low: number; high: number; count: number; label: string; range_label: string
  is_lunenburg: boolean
}

export type Test = {
  label: string; short: string; kind: string; unit: string
  old: number; old_moe: number; old_text: string
  new: number; new_moe: number; new_text: string
  difference: number; combined_moe: number; distinguishable: boolean
  difference_text: string; combined_moe_text: string; verdict: string
}

export function Caption({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[12.5px] leading-relaxed max-w-2xl mt-2"
      style={{ color: 'var(--text-muted)' }}>{children}</p>
  )
}

/** A chart's table. Same shape as every other report's, so a reader who has met one has
 *  met them all. */
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

const TIP = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5,
}

/** THE TOWN BY AGE, with every bar's margin on it. */
export function AgeProfile({ groups }: { groups: AgeGroup[] }) {
  const data = groups.map(g => ({
    label: g.label, estimate: g.estimate, err: g.moe,
    text: g.text, share: g.share_text,
  }))
  return (
    <>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 16, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
              axisLine={{ stroke: 'var(--axis)' }} tickLine={false} />
            <YAxis tickFormatter={n0} width={56}
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TIP} cursor={{ fill: 'var(--surface-3)' }}
              formatter={(_v, _k, p) => [p.payload.text + ' residents', p.payload.share]} />
            <Bar dataKey="estimate" fill={INK} radius={[4, 4, 0, 0]} maxBarSize={64}
              isAnimationActive={false}>
              <ErrorBar dataKey="err" stroke={MUTED} strokeWidth={2} width={8}
                direction="y" />
              <LabelList dataKey="share" position="top" offset={10}
                style={{ fontSize: 11, fill: 'var(--text-muted)' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableTwin
        caption="the same figures"
        head={['Age', 'Residents', 'Margin', 'Share of the town', 'Share margin']}
        rows={groups.map(g => [g.label, g.estimate_text, '± ' + g.moe_text,
          g.share_text, '± ' + g.share_moe_text])} />
    </>
  )
}

/** MEDIAN HOUSEHOLD INCOME BY AGE OF HOUSEHOLDER. Four separate medians of four
 *  separate sets of households — never a series through time, because it is not one. */
export function IncomeByAge({ all, bands }: { all: Est; bands: Est[] }) {
  const data = [all, ...bands].map(b => ({
    label: b.label, estimate: b.estimate, err: b.moe, text: b.text,
  }))
  return (
    <>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 16, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
              axisLine={{ stroke: 'var(--axis)' }} tickLine={false} />
            <YAxis tickFormatter={v => '$' + Math.round(v / 1000) + 'k'} width={56}
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TIP} cursor={{ fill: 'var(--surface-3)' }}
              formatter={(_v, _k, p) => [p.payload.text, 'median household income']} />
            <Bar dataKey="estimate" fill={INK} radius={[4, 4, 0, 0]} maxBarSize={64}
              isAnimationActive={false}>
              <ErrorBar dataKey="err" stroke={MUTED} strokeWidth={2} width={8}
                direction="y" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableTwin
        caption="the same figures"
        head={['Householder', 'Median household income', 'Margin']}
        rows={[all, ...bands].map(b => [b.label, b.estimate_text, '± ' + b.moe_text])} />
    </>
  )
}

/** WHERE THE TOWN STANDS IN MASSACHUSETTS — the shape of the queue, not the place in
 *  it. The bin Lunenburg falls in is marked; the two lines are the ends of its own
 *  interval, and the point of the chart is how much of the state sits between them. */
export function IncomeDistribution({ bins, low, high, estimate }: {
  bins: Bin[]; low: number; high: number; estimate: number
}) {
  return (
    <>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={bins} margin={{ top: 16, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            {/* No `interval` prop: recharts drops the ticks that would collide, which at
                390px leaves every other bin labelled. The table twin below carries all
                thirteen ranges, so nothing is lost by the thinning. */}
            <XAxis dataKey="label" height={30}
              tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
              axisLine={{ stroke: 'var(--axis)' }} tickLine={false} />
            <YAxis width={44} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TIP} cursor={{ fill: 'var(--surface-3)' }}
              formatter={(v, _k, p) => [`${v} municipalities`,
                p.payload.range_label + (p.payload.is_lunenburg
                  ? ' — including Lunenburg' : '')]} />
            <ReferenceLine x={bins.find(b => b.low <= low && low < b.high)?.label}
              stroke={MUTED} strokeDasharray="4 3" />
            <ReferenceLine x={bins.find(b => b.low <= high && high < b.high)?.label}
              stroke={MUTED} strokeDasharray="4 3" />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}
              isAnimationActive={false}>
              {bins.map(b => (
                <Cell key={b.label} fill={b.is_lunenburg ? MARK : INK} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableTwin
        caption="municipalities by median household income"
        head={['Median household income', 'Municipalities', 'Lunenburg']}
        rows={bins.map(b => [b.range_label, b.count, b.is_lunenburg ? 'here' : ''])}
        note={<>The dashed lines are the ends of Lunenburg&rsquo;s own interval, {usd0(low)} to{' '}
          {usd0(high)} around an estimate of {usd0(estimate)}. Every other
          municipality&rsquo;s figure has an interval of its own, which the bars do not
          draw.</>} />
    </>
  )
}

/** DID ANYTHING ACTUALLY CHANGE? Each difference between the two releases, in multiples
 *  of its own combined margin. Past 1 it clears; inside 1 it is not a change. */
export function MarginTest({ tests }: { tests: Test[] }) {
  // THE AXIS IS CAPPED AT THREE MARGINS AND THE CAP IS LABELLED. One comparison --
  // population -- clears by seventeen margins, because the survey controls the town
  // total to an independent estimate and its margin is ±19 where an age band's is in the
  // hundreds. Left uncapped, that one bar sets the scale and the fourteen others become
  // invisible slivers, which hides the whole finding. So the bar is drawn to the edge
  // and carries its true multiple as a label, and the table twin holds every real figure.
  const CAP = 3
  const data = tests.map(t => {
    const ratio = t.combined_moe ? t.difference / t.combined_moe : 0
    return {
      label: t.short, full: t.label,
      shown: Math.max(-CAP, Math.min(CAP, ratio)),
      capped: Math.abs(ratio) > CAP ? `${ratio.toFixed(1)}×` : '',
      clears: t.distinguishable,
      detail: `${t.old_text} → ${t.new_text}`,
      diff: `${t.difference_text} ± ${t.combined_moe_text}`,
    }
  }).sort((a, b) => Math.abs(b.shown) - Math.abs(a.shown))
  return (
    <>
      <div style={{ width: '100%', height: 28 * data.length + 56 }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical"
            margin={{ top: 8, right: 36, bottom: 8, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" domain={[-CAP, CAP]} allowDataOverflow
              ticks={[-3, -2, -1, 0, 1, 2, 3]}
              tickFormatter={v => (v === 0 ? '0' : `${v}×`)}
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="label" width={148}
              tick={{ fontSize: 10.5, fill: 'var(--text-secondary)' }}
              axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TIP} cursor={{ fill: 'var(--surface-3)' }}
              formatter={(_v, _k, p) => [p.payload.diff, p.payload.detail]}
              labelFormatter={(_l, p) => (p && p[0] ? p[0].payload.full : '')} />
            <ReferenceLine x={0} stroke="var(--axis)" />
            <ReferenceLine x={1} stroke={MARK} strokeDasharray="4 3" />
            <ReferenceLine x={-1} stroke={MARK} strokeDasharray="4 3" />
            <Bar dataKey="shown" radius={4} maxBarSize={14} isAnimationActive={false}>
              {data.map(r => (
                <Cell key={r.label} fill={INK} fillOpacity={r.clears ? 1 : 0.35} />
              ))}
              <LabelList dataKey="capped" position="right" offset={6}
                style={{ fontSize: 10.5, fill: 'var(--text-muted)' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableTwin
        caption="every comparison, and whether it clears its own margin"
        head={['Measure', 'Earlier release', 'Later release', 'Difference',
          'Combined margin', 'Verdict']}
        rows={tests.map(t => [t.label, t.old_text, t.new_text, t.difference_text,
          '± ' + t.combined_moe_text, t.verdict])}
        note={<>The dashed lines are one margin either side of no change: a bar that does
          not reach one of them is a difference this survey cannot see, which is not the
          same as one that did not happen. The axis stops at three margins, and a bar
          that runs past it carries its true multiple.</>} />
    </>
  )
}
