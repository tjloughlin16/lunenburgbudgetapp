import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceArea,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'

/** The charts for /what-stopped-being-funded. Every series arrives from
 *  /data/stopped-funding.json, written by scripts/build_stopped_funding.py — nothing here
 *  computes a figure and nothing here has one typed into it (rule 2).
 *
 *  COLOUR. The categorical question on this page has exactly two answers: the line was
 *  funded again, or it was not. So the encoding is ONE hue and one achromatic mark, and
 *  the hue is on the half that is the finding — a line that went to zero and stayed there.
 *  A line that came back is drawn in the axis ink, recessive on purpose: it is the thing
 *  that did NOT stop, and it is most of the series.
 *
 *  Two marks, both direct-labelled, both in the legend, and every chart has a table twin,
 *  so nothing on this page is carried by colour alone. No new palette token is introduced:
 *  --series-revenue and --axis are already validated against this surface, and a page that
 *  needs two categories does not need a set.
 *
 *  A YEAR WITH NO PRINTED ZEROS IS DRAWN AS NO EVIDENCE, NOT AS NONE. A zeroing is only
 *  visible if the book prints a zero, and the documents restating FY2023 onward print
 *  almost none. A bar of height zero there would say "nothing stopped that year", which is
 *  not what the data says — it says the instrument stopped recording. Those years get a
 *  shaded band and a label rather than a bar.
 *
 *  ONE AXIS PER PANEL, ALWAYS. Where a count and a dollar total are drawn together they
 *  are drawn as two stacked panels with their own axes, never as two axes on one frame,
 *  and the page never differences one against the other. */

export const STAYED = 'var(--series-revenue)'
export const RETURNED = 'var(--axis)'

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const pct = (x: number) => `${(x * 100).toFixed(0)}%`

/** A scrolling table twin. Wide content scrolls inside its own box; the page body never
 *  scrolls sideways. */
export function TableTwin({ head, rows, caption, max }: {
  head: string[]; rows: (string | number)[][]; caption?: string; max?: number
}) {
  return (
    <div className="mt-3">
      {caption && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>{caption}</p>
      )}
      <div className="overflow-auto -mx-1 px-1"
        style={max ? { maxHeight: max } : undefined}>
        <table className="text-[12.5px] tnum border-collapse min-w-full">
          <thead>
            <tr>{head.map((h, i) => (
              <th key={h} className="text-left font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
                style={{
                  color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right',
                  position: 'sticky', top: 0, background: 'var(--surface-1, var(--surface-3))',
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
    </div>
  )
}

/** One value, named, with the year as the heading. Written as a component rather than
 *  passed to recharts' `formatter`, whose signature admits an undefined value and would
 *  need a cast to use — and a cast is how a chart starts rendering `undefined`. */
function CoverTip({ active, payload, render }: {
  active?: boolean
  payload?: { payload: Cover }[]
  render: (c: Cover) => string
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 150 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="tnum" style={{ color: 'var(--text-secondary)' }}>{render(p)}</div>
    </div>
  )
}

/** Every series with a value in this year, named. A year a line is not printed carries no
 *  row here — it is a gap, not a zero. */
function NamedTip({ active, payload, label, names }: {
  active?: boolean; label?: number
  payload?: { dataKey?: string | number; value?: number | string }[]
  names: Record<string, string>
}) {
  if (!active || !payload?.length) return null
  const rows = payload.filter(p => typeof p.value === 'number')
  if (!rows.length) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 240 }}>
      <div className="font-bold mb-1">{fy(Number(label))}</div>
      {rows.map(p => (
        <div key={String(p.dataKey)} className="flex justify-between gap-4">
          <span style={{ color: 'var(--text-secondary)' }}>
            {names[String(p.dataKey)] ?? String(p.dataKey)}
          </span>
          <span className="tnum">{usd(p.value as number)}</span>
        </div>
      ))}
    </div>
  )
}

function Key({ items }: { items: { color: string; label: string }[] }) {
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

/* --------------------------------------------------- how much stopped, year by year */

export type Year = {
  fy: number; n: number; dollars: number; zeros_printed: number
  returned_n: number; returned_dollars: number
  stayed_n: number; stayed_dollars: number; lines_both_years: number
}

function YearTip({ active, payload, silent }: {
  active?: boolean; payload?: { payload: Year }[]; silent: number[]
}) {
  if (!active) return null
  const p = payload?.[0]?.payload
  if (!p) return null
  if (silent.includes(p.fy)) {
    return (
      <div className="card p-2.5 text-[12px]" style={{ minWidth: 220 }}>
        <div className="font-bold mb-1">{fy(p.fy)}</div>
        <div style={{ color: 'var(--text-muted)' }}>
          No evidence either way. The book restating this year prints {p.zeros_printed}{' '}
          zeros in all, and no line in it goes from funded to zero.
        </div>
      </div>
    )
  }
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 220 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Went to zero and stayed</span>
        <span className="tnum">{p.stayed_n} &middot; {usd(p.stayed_dollars)}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Went to zero, funded again</span>
        <span className="tnum">{p.returned_n} &middot; {usd(p.returned_dollars)}</span>
      </div>
      <div className="mt-1.5" style={{ color: 'var(--text-muted)' }}>
        out of {p.lines_both_years} lines printed in both years
      </div>
    </div>
  )
}

/** The prior year's funding on every line the book took to zero, split by whether the line
 *  was ever funded again. Stacked because the two parts are parts of one quantity. */
export function ZeroedByYear({ years, silent }: { years: Year[]; silent: number[] }) {
  const band = silent.length
    ? [Math.min(...silent) - 0.5, Math.max(...silent) + 0.5] as const
    : null
  return (
    <div className="mt-5">
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={years} margin={{ top: 14, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="20%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" type="number" domain={['dataMin - 0.5', 'dataMax + 0.5']}
              tickFormatter={fy} ticks={years.map(y => y.fy)} tick={{ fontSize: 11 }}
              stroke="var(--axis)" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={64} />
            {band && (
              <ReferenceArea x1={band[0]} x2={band[1]} fill="var(--axis)" fillOpacity={0.16}
                label={{ value: 'no printed zeros — no evidence either way',
                  position: 'insideTop', fontSize: 10, fill: 'var(--text-muted)' }} />
            )}
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={<YearTip silent={silent} />} />
            <Bar dataKey="returned_dollars" stackId="a" isAnimationActive={false}
              fill={RETURNED} />
            <Bar dataKey="stayed_dollars" stackId="a" isAnimationActive={false}
              fill={STAYED} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: STAYED, label: 'went to zero and was never funded again' },
        { color: RETURNED, label: 'went to zero and was funded again later' },
      ]} />
    </div>
  )
}

/* ------------------------------------------------------------ what the money bought */

export type Cut = { name: string; n: number; dollars: number }

/** Ranked bars on a common baseline. One quantity, one hue, direct-labelled — the reader's
 *  question is how one category compares with the others, and length on a shared baseline
 *  is the only encoding that answers it without arithmetic. */
export function ByCategory({ cuts, unit }: { cuts: Cut[]; unit: string }) {
  const top = Math.max(...cuts.map(c => c.dollars), 1)
  return (
    <div className="mt-5 flex flex-col gap-2.5">
      {cuts.map(c => (
        <div key={c.name}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] font-semibold">{c.name}</span>
            <span className="text-[12.5px] tnum whitespace-nowrap"
              style={{ color: 'var(--text-secondary)' }}>
              {usd(c.dollars)} &middot; {c.n} {unit}
            </span>
          </div>
          <div className="mt-1 rounded-[3px]" style={{ background: 'var(--surface-3)', height: 14 }}>
            <div className="rounded-[3px]" style={{
              width: `${Math.max(1.2, (c.dollars / top) * 100)}%`,
              height: 14, background: STAYED,
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}

/* --------------------------------------------------- the book's own shape, year by year */

export type Cover = {
  fy: number; lines: number; zeros: number; total: number; documents: number
}

/** TWO PANELS, TWO AXES, NEVER ONE FRAME. How many lines the book prints, and what those
 *  lines come to. They are a count and a dollar total: drawing them on one pair of axes
 *  would invite the eye to read a ratio that means nothing, and the page never differences
 *  one against the other. Both share the same x. */
export function ShapeOfTheBook({ coverage, markFy }: { coverage: Cover[]; markFy: number }) {
  const ticks = coverage.map(c => c.fy)
  const mark = markFy + 0.5
  return (
    <div className="mt-5 flex flex-col gap-5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
          style={{ color: 'var(--text-muted)' }}>Lines the book prints</p>
        <div style={{ height: 170 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={coverage} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" type="number" domain={['dataMin - 0.5', 'dataMax + 0.5']}
                ticks={ticks} tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--axis)" width={44} />
              <ReferenceArea x1={mark} x2={Math.max(...ticks) + 0.5} fill="var(--axis)"
                fillOpacity={0.12} />
              <Tooltip cursor={{ fill: 'var(--surface-3)' }}
                content={<CoverTip render={c => `${c.lines} lines printed`} />} />
              <Bar dataKey="lines" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                {coverage.map(c => (
                  <Cell key={c.fy} fill={c.fy > markFy ? STAYED : RETURNED} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
          style={{ color: 'var(--text-muted)' }}>What those lines come to</p>
        <div style={{ height: 170 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={coverage} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" type="number" domain={['dataMin - 0.5', 'dataMax + 0.5']}
                ticks={ticks} tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
              <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
                width={64} />
              <ReferenceArea x1={mark} x2={Math.max(...ticks) + 0.5} fill="var(--axis)"
                fillOpacity={0.12} />
              <Tooltip content={
                <CoverTip render={c => `${usd(c.total)} restated total`} />} />
              <Line type="monotone" dataKey="total" stroke={STAYED} strokeWidth={2}
                dot={{ r: 2.5 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------- one family of lines, over time */

export type Named = {
  line_key: string; label: string; points: { fy: number; value: number }[]
  last_fy: number; last_value: number
}

const NAMED_INK = ['var(--series-revenue)', 'var(--series-cost)', 'var(--fund-school)',
                   'var(--fund-enterprise)', 'var(--text-muted)']

/** A named family of lines across the span. A year the book does not print is a GAP, never
 *  a zero — `connectNulls` is off for exactly that reason, and the table twin says
 *  "not printed" rather than leaving a blank cell. */
export function NamedLines({ lines, span }: { lines: Named[]; span: number[] }) {
  const rows = span.map(f => {
    const r: Record<string, number | null> = { fy: f }
    lines.forEach(l => {
      const p = l.points.find(x => x.fy === f)
      r[l.line_key] = p ? p.value : null
    })
    return r
  })
  return (
    <div className="mt-5">
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }} stroke="var(--axis)" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={64} />
            <Tooltip content={<NamedTip
              names={Object.fromEntries(lines.map(l => [l.line_key, l.label]))} />} />
            {lines.map((l, i) => (
              <Line key={l.line_key} type="linear" dataKey={l.line_key}
                stroke={NAMED_INK[i % NAMED_INK.length]} strokeWidth={2}
                dot={{ r: 2.5 }} connectNulls={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Key items={lines.map((l, i) => ({
        color: NAMED_INK[i % NAMED_INK.length], label: l.label,
      }))} />
    </div>
  )
}
