import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

/* Recharts hands a tooltip value as `ValueType | undefined` -- a string, a number or an
 * array of either. Every formatter here wants a number, so it is coerced once, here,
 * rather than asserted at each call site. */
const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))


/* ONE PIE, BUILT ONCE, BECAUSE THE DEFAULT ONE HAD FOUR FAULTS AND THREE PAGES USE IT.
 *
 * TJ, 22 September 2026, with a screenshot: *"make sure the charts look good."* On the
 * budget pie: the `57%` label was cut off by the top of the frame, the legend ran off the
 * left edge mid-word (`ral Purchasing`), the legend was in ALPHABETICAL order so the
 * smallest department came first on a chart whose entire subject is size, and the tooltip
 * was grey-on-grey and barely readable over the slices.
 *
 * Each of those is recharts' default doing something reasonable in general and wrong here:
 *
 *  - OUTSIDE LABELS WITH LEADER LINES need room the frame does not have, and the biggest
 *    slice's label is the one that runs off the top. Labels are drawn INSIDE the slice
 *    instead, in white, and only where the slice is wide enough to hold one.
 *  - THE BUILT-IN LEGEND lays itself out in a fixed row that clips rather than wraps, and
 *    orders its entries its own way. This one is ordinary HTML: it wraps, it is ranked
 *    largest first like the table under it, and it carries each slice's VALUE so the
 *    small ones -- which a pie is genuinely bad at -- are still readable.
 *  - THE TOOLTIP inherits muted text. Colours are set explicitly.
 */

export type Slice = { key: string; name: string; value: number }

export function PieWithLegend({
  rows, colours, format, height = 300, minLabel = 0.05,
}: {
  rows: Slice[]
  colours: string[]
  format: (v: number) => string
  height?: number
  minLabel?: number
}) {
  const ranked = [...rows].sort((a, b) => b.value - a.value)
  const total = ranked.reduce((s, r) => s + r.value, 0)
  const pct = (v: number) => (total ? (v / total) * 100 : 0)
  return (
    <div>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer>
          <PieChart margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
            <Pie data={ranked} dataKey="value" nameKey="name" outerRadius="92%"
              isAnimationActive={false} stroke="var(--surface-1)" strokeWidth={2}
              labelLine={false}
              label={(p: { percent?: number; cx?: number; cy?: number; midAngle?: number
                           innerRadius?: number; outerRadius?: number }) => {
                if ((p.percent ?? 0) < minLabel) return null
                // Placed at 62% of the radius, which keeps a label inside its own slice
                // at every size a slice of this share can be.
                const RAD = Math.PI / 180
                const r = (p.innerRadius ?? 0) + ((p.outerRadius ?? 0) - (p.innerRadius ?? 0)) * 0.62
                const x = (p.cx ?? 0) + r * Math.cos(-(p.midAngle ?? 0) * RAD)
                const y = (p.cy ?? 0) + r * Math.sin(-(p.midAngle ?? 0) * RAD)
                return (
                  <text x={x} y={y} fill="#ffffff" fontSize={12} fontWeight={700}
                    textAnchor="middle" dominantBaseline="central">
                    {Math.round((p.percent ?? 0) * 100)}%
                  </text>
                )
              }}>
              {ranked.map((r, i) => (
                <Cell key={r.key} fill={colours[i % colours.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: 'var(--surface-1)', border: '1px solid var(--grid)',
                borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
                boxShadow: '0 2px 10px rgba(0,0,0,.10)',
              }}
              itemStyle={{ color: 'var(--text-primary)' }}
              labelStyle={{ color: 'var(--text-primary)' }}
              formatter={(v, n) =>
                [`${format(N(v))} · ${pct(N(v)).toFixed(1)}%`, n]} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 list-none p-0 m-0">
        {ranked.map((r, i) => (
          <li key={r.key} className="flex items-baseline gap-2 text-[12px]">
            <span aria-hidden className="inline-block rounded-[2px]"
              style={{
                width: 10, height: 10, background: colours[i % colours.length],
                transform: 'translateY(1px)',
              }} />
            <span style={{ color: 'var(--text-primary)' }}>{r.name}</span>
            <span className="tnum" style={{ color: 'var(--text-muted)' }}>
              {format(r.value)} · {pct(r.value).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
