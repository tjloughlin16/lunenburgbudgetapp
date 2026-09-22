import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'
import { PieWithLegend } from './PieWithLegend'
import { Scene } from './Scene'

/* The charts for /analysis/town-budgets, from /data/town-budgets.json. Rule 7f. */

// A CATEGORICAL PALETTE, VALIDATED RATHER THAN CHOSEN. TJ: *"the colors have to be
// distinct enough. the personel page is hard to see the differences."* The old one ran
// four BLUES in a row -- #12325f, #184f95, #3f78bd, #7ea6d8 -- so the four biggest
// departments, which are the four a reader cares most about telling apart, were four
// shades of one hue.
//
// Checked with the dataviz validator rather than by eye (`scripts/validate_palette.js`
// in the bundled skill), against this surface, in this ORDER -- the checks are on
// ADJACENT pairs and these charts are ranked by size, so adjacent means adjacent in rank:
//
//   lightness band       all 12 inside L 0.43-0.77      PASS
//   chroma floor         all 12 >= 0.1                  PASS
//   CVD separation       worst adjacent dE 8.4 protan   PASS
//   normal-vision floor  worst adjacent dE 19.6         PASS
//   contrast vs surface  three below 3:1                WARN -- see below
//
// The contrast warning is not dismissable and is not dismissed: it obliges visible labels
// or a table view, and every chart using this palette carries a legend naming each series
// with its value, plus the same figures as a table further down the page.
//
// DARK MODE IS NOT THIS PALETTE FLIPPED. Three of these fall outside the band the
// validator wants against the dark surface, and the honest fix is a second set of steps
// chosen for that surface rather than a reuse of these. These SVGs are fixed-colour files
// served to /docs and to the PDF, so they use the light set; picking the dark steps is
// open work.
const SLICES = ['#2b6cb0', '#dc2626', '#ea8c00', '#2f8f4e', '#7c3aed', '#0d9488', '#92400e', '#c026d3', '#38bdf8', '#a3a324', '#e0558a', '#3b5bbf']

type Dept = {
  name: string; slug: string; last: number; first: number; share: number
  rate: number; excess: number; pull: number; series: Record<string, number>
}
type Total = { fy: number; voted: number; status: string }
type Payload = {
  departments: Dept[]; detail_years: number[]; levy_cap: number
  totals: Total[]; prose?: { fy?: string }
  pictogram: { unit: number; unit_label: string; glyphs: Record<string, string> }
}

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usdk = (v: number) =>
  Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M`
    : Math.abs(v) >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`

const usd = (v: number) => '$' + Math.round(v).toLocaleString()

/** THE SIGNATURE IMAGE: the voted budget as a town you can look at. */
export function TownBudgetsTown({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.departments.filter(r => r.last).sort((a, b) => b.last - a.last)
  const unit = 100000
  // AT LEAST ONE ICON EACH. At a million, four of the twelve would be drawn as nothing,
  // and a picture that silently omits the smallest departments makes a claim the budget
  // does not.
  const items = rows.flatMap((r, i) =>
    Array.from({ length: Math.max(1, Math.round(r.last / unit)) }, () => ({
      glyph: d.pictogram.glyphs[r.slug] ?? d.pictogram.glyphs['central-purchasing'],
      colour: SLICES[i % SLICES.length],
    })))
  return (
    <Scene items={items} cols={50} cell={26}
      label={`One icon is $100,000 of the voted budget: ${items.length} icons, each department drawn in a thing it buys.`}
      keys={rows.map((r, i) => ({
        label: r.name, note: usdk(r.last), colour: SLICES[i % SLICES.length],
      }))} />
  )
}

/** A pie: how the voted budget divides between the twelve departments. */
export function TownBudgetsShare({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.departments.filter(r => r.last)
    .map(r => ({ key: r.slug, name: r.name, value: r.last }))
  return <PieWithLegend rows={rows} colours={SLICES} format={usd} height={320} />
}

/** Every department on ONE dollar axis: the relation the small multiples hide. */
export function TownBudgetsAll({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.departments.filter(r => r.last).sort((a, b) => b.last - a.last)
  const wide = d.detail_years.map(y => {
    const row: Record<string, number | string> = { fy: `FY${y}` }
    for (const r of rows) row[r.name] = r.series[String(y)]
    return row
  })
  return (
    <div style={{ width: '100%', height: 380 }}>
      <ResponsiveContainer>
        <LineChart data={wide} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tickFormatter={usdk} width={52}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box} formatter={(v: number) => usd(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />
          {rows.map((r, i) => (
            <Line key={r.slug} dataKey={r.name} type="linear"
              stroke={SLICES[i % SLICES.length]} strokeWidth={2} dot={{ r: 2.5 }}
              isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/* THE CAP IS A REFERENCE LINE, NOT A THRESHOLD ANYBODY BREACHED. Proposition 2.5 limits
 * the LEVY, not the budget, and the page says so in words; the line is here because every
 * board in town already reads growth against it. */
export function TownBudgetsRates({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.departments.filter(r => r.rate !== undefined)
    .sort((a, b) => b.rate - a.rate)
  return (
    <div style={{ width: '100%', height: Math.max(240, rows.length * 30 + 48) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis type="category" dataKey="name" width={188}
            tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
          <Tooltip contentStyle={box}
            formatter={(v: number) => [`${v.toFixed(1)}% a year`, 'growth']} />
          <ReferenceLine x={d.levy_cap} stroke="#8a5210" strokeDasharray="4 3"
            label={{ value: `Prop 2½ · ${d.levy_cap}%`, position: 'top',
                     fontSize: 11, fill: '#8a5210' }} />
          <Bar dataKey="rate" isAnimationActive={false} radius={[0, 3, 3, 0]}>
            {rows.map(r => (
              <Cell key={r.slug} fill={r.rate >= d.levy_cap ? '#184f95' : '#22795a'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Diverging bars: dollars a year each department runs above the cap. */
export function TownBudgetsPull({ data }: ChartProps) {
  const rows = [...(data as Payload).departments].sort((a, b) => b.excess - a.excess)
  return (
    <div style={{ width: '100%', height: Math.max(240, rows.length * 30 + 48) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={usdk}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis type="category" dataKey="name" width={188}
            tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
          <Tooltip contentStyle={box}
            formatter={(v: number) => [`${usd(v)} a year above the cap`, '']} />
          <ReferenceLine x={0} stroke="var(--text-muted)" />
          <Bar dataKey="excess" isAnimationActive={false} radius={[0, 3, 3, 0]}>
            {rows.map(r => (
              <Cell key={r.slug} fill={r.excess >= 0 ? '#184f95' : '#22795a'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** One panel per department, each on its own scale: how its money moved. */
export function TownBudgetsTrends({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.departments.filter(r => r.last).sort((a, b) => b.last - a.last)
  return (
    <div className="grid gap-4"
      style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))' }}>
      {rows.map((r, i) => (
        <div key={r.slug}>
          <div className="text-[12px] font-semibold" style={{ color: 'var(--text-primary)' }}>
            {r.name}
          </div>
          <div className="text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
            {usdk(r.last)} · {r.rate.toFixed(1)}% a year
          </div>
          <div style={{ width: '100%', height: 116 }}>
            <ResponsiveContainer>
              {/* THE CAP LINE CAME BACK. TJ: *"for the charts on 'How each department is
                  growing' we lost the prop 2.5 lines."* The generated SVG drew a faint
                  line at what the department would be if it had grown at the levy cap
                  from its first year, and the conversion dropped it -- which removes the
                  only thing on a panel that says whether the shape is fast or slow.
                  It is a REFERENCE, not a limit: Proposition 2½ caps the levy, not the
                  budget, and the page says so in words. */}
              <LineChart data={d.detail_years.map(y => ({
                fy: `FY${y}`,
                amount: r.series[String(y)],
                cap: r.first * Math.pow(1 + d.levy_cap / 100,
                                        y - d.detail_years[0]),
              }))} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tickFormatter={usdk} width={46}
                  domain={['dataMin', 'dataMax']}
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={box}
                  formatter={(v: number, n: string) =>
                    [usd(v), n === 'cap' ? `at the ${d.levy_cap}% levy cap` : 'voted']} />
                <Line dataKey="cap" name="cap" type="linear" dot={false}
                  stroke="#8a5210" strokeWidth={1.4} strokeDasharray="4 3"
                  isAnimationActive={false} />
                <Line dataKey="amount" name="voted" type="linear" dot={{ r: 2.5 }}
                  stroke={SLICES[i % SLICES.length]} strokeWidth={2}
                  isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  )
}


/* THE LAST COLUMN IS A DIFFERENT KIND OF FIGURE and is coloured to say so. Every other
 * year is a grand total with a department table printed beneath it that this project has
 * read; FY2026 is a total printed as PROSE in a town-meeting article, with no department
 * detail published in any form. Same axis, same units, different evidence -- and a
 * reader who cannot see that difference will quote the last column like the rest. */
export function TownBudgetsTotal({ data }: ChartProps) {
  const d = data as Payload
  const rows = [...d.totals].sort((a, b) => a.fy - b.fy).map((t, i, all) => ({
    fy: `FY${t.fy}`,
    voted: t.voted,
    change: i ? (t.voted / all[i - 1].voted - 1) * 100 : null,
    prose: String(t.fy) === String(d.prose?.fy),
  }))
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" />
          <YAxis tickFormatter={usdk} width={52}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box}
            formatter={(v: number, _n: string, p: { payload?: typeof rows[number] }) =>
              [`${usd(v)}${p.payload?.change === null || p.payload?.change === undefined
                ? '' : ` · ${p.payload.change >= 0 ? '+' : ''}${p.payload.change.toFixed(1)}%`}`,
               p.payload?.prose ? 'voted — printed as prose, no department table' : 'voted']} />
          <Bar dataKey="voted" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {rows.map(r => (
              <Cell key={r.fy} fill={r.prose ? '#e08214' : '#184f95'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
