/** REGISTRATION DEPOSITS BY THE MONTH OF SALE (parks-year-changes). TJ, 19 November 2026: "a
 *  page that compared year over year to identify what changed in either revenue or spending".
 *
 *  One row a fiscal year, one cell a month of SALES -- the month a MyRec deposit's memo names
 *  (`PROG/SEP2024 PARK MYREC`), which is our reading of the memo, not a field the Town keeps. An
 *  empty cell is a month no deposit names. Tap a cell for every line placed in it: deposits,
 *  refunds, card charges and same-day corrections, each with the year it posted in. Every string
 *  is formatted by scripts/build_parks_ledger.py; this scales the cells by the numbers. */
import { useState } from 'react'
import type { CustomProps } from './index'

type Line = { d: string; what: string; acct: string; k: 'deposit' | 'refund' | 'charge' | 'correction'; amt: string; posted: string }
type Cell = { m: string; net: number; t: string; ts: string; has: boolean; lines: Line[] }
type Year = { fy: string; t: string; t_empty: string; cells: Cell[] }
type Data = { years: Year[]; max: number; months: string[]; text: Record<string, string> }

const IN = 'var(--thread-1)'
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

export default function ParkSalesMonths({ data, alt }: CustomProps) {
  const d = data as Data
  const [at, setAt] = useState<[number, number] | null>(null)
  const sel = at ? d.years[at[0]].cells[at[1]] : null
  return (
    <div aria-label={alt} className="max-w-3xl">
      {/* divs, not a table: the site adds download links to every <table> */}
      <div className="overflow-x-auto">
        <div className="grid gap-[3px] text-[12px] tabular-nums min-w-[560px] items-center"
          style={{ gridTemplateColumns: '3.6rem repeat(12, minmax(0, 1fr)) auto' }}>
          <span />
          {d.months.map(m => <span key={m} className="text-center" style={muted}>{m}</span>)}
          <span />
          {d.years.map((y, yi) => [
            <span key={`${y.fy}h`} className="font-semibold whitespace-nowrap">{y.fy}</span>,
            ...y.cells.map((c, ci) => {
              const on = at?.[0] === yi && at?.[1] === ci
              const a = c.has ? 0.18 + 0.82 * Math.max(c.net, 0) / d.max : 0
              return (
                <button key={`${y.fy}${c.m}`} type="button" onClick={() => setAt(on ? null : [yi, ci])} aria-pressed={on}
                  aria-label={`${y.fy} ${c.m}: ${c.has ? c.t : d.text.none}`}
                  className="w-full h-11 rounded-sm flex items-end justify-center pb-0.5"
                  style={{ background: c.has ? `color-mix(in srgb, ${IN} ${Math.round(a * 100)}%, transparent)` : 'transparent',
                    border: c.has ? 'none' : '1px dashed var(--text-muted)',
                    outline: on ? '2px solid var(--text-primary)' : 'none' }}>
                  <span className="text-[10.5px] leading-none" style={{ color: a > 0.6 ? 'var(--surface-1)' : 'var(--text-secondary)' }}>
                    {c.has ? c.ts : ''}</span>
                </button>)
            }),
            <span key={`${y.fy}e`} className="pl-2 text-[11.5px] whitespace-nowrap" style={muted}>{y.t_empty}</span>,
          ])}
        </div>
      </div>
      <p className="text-[12px] mt-1" style={muted}>{d.text.ours}</p>
      <div className="mt-3 text-[13.5px]">
        {!sel && <p style={muted}>{d.text.pick}</p>}
        {sel && at && (<>
          <p className="font-semibold mb-1">{sel.m}, {d.years[at[0]].fy}{sel.lines.length ? ` · ${sel.t}` : ''}</p>
          {!sel.lines.length && <p style={muted}>{d.text.none}</p>}
          <ul className="divide-y" style={{ borderColor: 'var(--grid)' }}>
            {sel.lines.map((l, i) => (
              <li key={i} className="py-1.5 grid grid-cols-[1fr_auto] gap-x-3" style={{ borderColor: 'var(--grid)' }}>
                <span className="min-w-0">
                  <span>{d.text[l.k]}</span> <span style={muted}>· {l.acct}</span>
                  <span className="block text-[12.5px] break-words" style={muted}>{l.d} · {l.what} · {d.text.posted} {l.posted}</span>
                </span>
                <span className="tabular-nums" style={l.k === 'deposit' ? undefined : secondary}>{l.amt}</span>
              </li>))}
          </ul>
        </>)}
      </div>
    </div>)
}
