import {
  Area, AreaChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'
import { PieWithLegend } from './PieWithLegend'
import { Scene } from './Scene'
import { Pictogram } from './Pictogram'

/* Recharts hands a tooltip value as `ValueType | undefined` -- a string, a number or an
 * array of either. Every formatter here wants a number, so it is coerced once, here,
 * rather than asserted at each call site. */
const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))

/* The charts for /analysis/town-personnel, rendered from /data/town-personnel.json --
 * the same payload that feeds the stat row and the conclusions, so there is one set of
 * figures and not one for the page and another for a picture (rules 2 and 7f).
 *
 * `isAnimationActive={false}` throughout: recharts animates on mount and the headless
 * capture used for screenshots takes its picture before the animation finishes, which
 * renders the chart blank in exactly the image somebody is reviewing it from. */

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

type Employer = {
  department: string; people: number; years: number; kind: string
  first: number; first_fy: string; last_fy: string; suspect: string[]
  series: { fy: string; people: number; suspect: boolean }[]
}
type Fire = { fy: string; career: number; on_call_low: number; on_call_high: number }
type Payload = {
  employers: Employer[]; fire: Fire[]
  pictogram: { unit: number; unit_label: string; glyph: string }
}

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}

/** THE SIGNATURE IMAGE: everybody the town publishes a count for, as a crowd. */
export function TownPersonnelCrowd({ data }: ChartProps) {
  const d = data as Payload
  const emp = [...d.employers].sort((a, b) => b.people - a.people)
  const items = emp.flatMap((e, i) =>
    Array.from({ length: e.people }, () => ({
      glyph: d.pictogram.glyph, colour: SLICES[i % SLICES.length],
    })))
  return (
    <Scene items={items} cols={46} cell={24}
      label={`One figure is one person: ${items.length} people across ${emp.length} departments, the schools most of them.`}
      keys={emp.map((e, i) => ({
        label: e.department, note: String(e.people),
        colour: SLICES[i % SLICES.length],
      }))} />
  )
}

/** A pie: how the people the town publishes a count for divide between departments. */
export function TownPersonnelShare({ data }: ChartProps) {
  const rows = (data as Payload).employers
    .map(e => ({ key: e.department, name: e.department, value: e.people }))
  return (
    <PieWithLegend rows={rows} colours={SLICES} height={320}
      format={(v: number) => `${N(v)} ${v === 1 ? 'person' : 'people'}`} />
  )
}

/* A YEAR WITH NO FIGURE IS A HOLE, NOT A ZERO, and recharts needs it spelled that way:
 * a missing year must be `null`, and `connectNulls` must stay off, or the line is drawn
 * straight across three years the Council on Aging published nothing in. Every series
 * here is therefore built against the full span of years rather than against its own
 * points. */
function wide(emp: Employer[]) {
  const years = [...new Set(emp.flatMap(e => e.series.map(p => +p.fy)))].sort((a, b) => a - b)
  const span: number[] = []
  for (let y = years[0]; y <= years[years.length - 1]; y++) span.push(y)
  return span.map(y => {
    const row: Record<string, number | string | null> = { fy: `FY${y}` }
    for (const e of emp) {
      const p = e.series.find(s => +s.fy === y && !s.suspect)
      row[e.department] = p ? p.people : null
    }
    return row
  })
}

/** Every department on one people axis: the size relation the panels deliberately hide. */
export function TownPersonnelAll({ data }: ChartProps) {
  const emp = [...(data as Payload).employers].sort((a, b) => b.people - a.people)
  return (
    <div style={{ width: '100%', height: 380 }}>
      <ResponsiveContainer>
        <LineChart data={wide(emp)} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={40} />
          <Tooltip contentStyle={box} />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />
          {emp.map((e, i) => (
            <Line key={e.department} dataKey={e.department} type="linear"
              stroke={SLICES[i % SLICES.length]} strokeWidth={2} dot={{ r: 2.5 }}
              connectNulls={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** One panel per department, each on its OWN scale: how each is moving, not how big. */
export function TownPersonnelCounts({ data }: ChartProps) {
  const emp = (data as Payload).employers
    .filter(e => e.series.filter(p => !p.suspect).length >= 2)
    .sort((a, b) => b.people - a.people)
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))' }}>
      {emp.map((e, i) => {
        const pts = e.series.filter(p => !p.suspect)
          .map(p => ({ fy: `FY${p.fy}`, people: p.people }))
        return (
          <div key={e.department}>
            <div className="text-[12px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {e.department}
            </div>
            <div className="text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
              FY{e.first_fy}–FY{e.last_fy} · {e.people} now · {e.kind}
            </div>
            <div style={{ width: '100%', height: 128 }}>
              <ResponsiveContainer>
                <LineChart data={pts} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="fy" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                    interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} width={32}
                    domain={['dataMin', 'dataMax']} />
                  <Tooltip contentStyle={box} />
                  <Line dataKey="people" type="linear" dot={{ r: 2.5 }}
                    stroke={SLICES[i % SLICES.length]} strokeWidth={2}
                    isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )
      })}
    </div>
  )
}


/** The same data the bars carried, drawn in figures. TJ: the icon one is more
 *  interesting than the basic bar chart and is identical data wise. */
export function TownPersonnelPeople({ data }: ChartProps) {
  const d = data as Payload
  const emp = [...d.employers].sort((a, b) => b.people - a.people)
  return (
    <Pictogram unit={d.pictogram.unit} unitLabel={d.pictogram.unit_label} max={25}
      size={18}
      rows={emp.map((e, i) => ({
        key: e.department, label: e.department, value: e.people,
        note: String(e.people), glyph: d.pictogram.glyph,
        colour: SLICES[i % SLICES.length],
      }))} />
  )
}

/* THE ON-CALL ROLL IS A RANGE THE TOWN PRINTS, not a number it prints. Drawing a line
 * through the middle of `30-35` would publish a figure the town never stated, so the
 * range is drawn as a BAND between its ends and the career count as a line across it.
 * Rule 13a: publish the spread rather than choosing inside it. */
export function TownPersonnelFire({ data }: ChartProps) {
  const rows = (data as Payload).fire.map(f => ({
    fy: `FY${f.fy}`, career: f.career,
    band: [f.on_call_low, f.on_call_high] as [number, number],
  }))
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <AreaChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={36} />
          <Tooltip contentStyle={box}
            formatter={(v, n) =>
              [Array.isArray(v) ? `${v[0]}\u2013${v[1]}` : v,
               n === 'band' ? 'on call, as printed' : 'career']} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area dataKey="band" name="on call, as printed" stroke="#e08214"
            fill="#e08214" fillOpacity={0.22} isAnimationActive={false} />
          <Line dataKey="career" name="career" stroke="#12325f" strokeWidth={2}
            dot={{ r: 3 }} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
