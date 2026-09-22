import {
  CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'
import { PieWithLegend } from './PieWithLegend'

/* Recharts hands a tooltip value as `ValueType | undefined` -- a string, a number or an
 * array of either. Every formatter here wants a number, so it is coerced once, here,
 * rather than asserted at each call site. */
const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))

/* The charts for /analysis/board-composition, from /data/board-composition.json.
 * Rule 7f: a chart is a component, never an image. Nothing here computes a figure. */

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
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}

type Size = { post: string; people: number }
type Fill = { fy: string; bodies: number; seats: number; filled: number; pct: number }
type Payload = { sizes: Size[]; fill: Fill[] }

const TOP = 10

/** A pie of every filled post by body, with the long tail gathered rather than dropped. */
export function BoardCompositionWhere({ data }: ChartProps) {
  const sizes = [...(data as Payload).sizes].sort((a, b) => b.people - a.people)
  const head = sizes.slice(0, TOP)
  const tail = sizes.slice(TOP)
  // THE TAIL IS GATHERED, NOT DROPPED. Fifty single-holder posts are a real part of the
  // whole, and a pie that quietly omits them is a pie of a different quantity.
  const rows = [
    ...head.map(r => ({ key: r.post, name: r.post, value: r.people })),
    ...(tail.length ? [{
      key: '_tail',
      name: `${tail.length} smaller bodies and single-holder posts`,
      value: tail.reduce((s, r) => s + r.people, 0),
    }] : []),
  ]
  return (
    <PieWithLegend rows={rows} colours={SLICES} height={320}
      format={(v: number) => `${N(v)} ${v === 1 ? 'person' : 'people'}`} />
  )
}

/* A HUNDRED PER CENT IS THE INTERESTING LINE, not the top of the axis. The charters say
 * how many seats exist; the listing says how many names are printed against them, and
 * early years print MORE names than seats -- associate members, holdovers, a seat filled
 * twice in one year. So the reference line is drawn at 100 and the axis is left to go
 * above it, because a chart clipped at 100 would hide the thing that needs explaining. */
export function BoardCompositionFill({ data }: ChartProps) {
  const fill = (data as Payload).fill.map(f => ({ ...f, label: `FY${f.fy}` }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={fill} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tickFormatter={(v: number) => `${N(v)}%`} width={48}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box}
            formatter={(v, _n, p: { payload?: Fill }) =>
              [`${N(v).toFixed(1)}% — ${p.payload?.filled} names against ${p.payload?.seats} `
               + `seats across ${p.payload?.bodies} bodies`, 'filled']} />
          <ReferenceLine y={100} stroke="#8a5210" strokeDasharray="4 3"
            label={{ value: 'every seat filled', position: 'right', fontSize: 11,
                     fill: '#8a5210' }} />
          <Line dataKey="pct" type="linear" stroke="#184f95" strokeWidth={2}
            dot={{ r: 3.5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
