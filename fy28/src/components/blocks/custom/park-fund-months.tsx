/** THE PARKS FEE FUND, MONTH BY MONTH (park-revolving-fund). Fund 1500's journal, FY2023 to the
 *  FY2026 close: what came in each month above the line, what was paid out below it, and every
 *  receipt and payment of the month a reader taps. A month is the journal's PERIOD (period 13, the close, is
 *  drawn with June). Every figure and string is formatted by scripts/build_parks_topics.py; this
 *  scales bars by the numbers and prints the given text. */
import { useState } from 'react'
import type { CustomProps } from './index'

type Pay = { d: string; who: string; what: string; amt: string }
type Month = { m: string; in: number; out: number; t_in: string; t_out: string; pays: Pay[]; ins: Pay[] }
type Year = { fy: string; t_in: string; t_out: string; t_close: string; months: Month[] }
type Data = { years: Year[]; max: number
  text: { in: string; out: string; close: string; pick: string; none: string; ins: string; pays: string } }

const IN = 'var(--thread-1)', OUT = 'var(--thread-3)'
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

export default function ParkFundMonths({ data, alt }: CustomProps) {
  const d = data as Data
  const [yi, setYi] = useState(d.years.length - 1)
  const [mi, setMi] = useState<number | null>(null)
  const y = d.years[yi]
  const H = 70                                   // px for the largest month, each side
  const sel = mi === null ? null : y.months[mi]
  return (
    <div aria-label={alt} className="max-w-3xl">
      <div className="flex flex-wrap gap-1.5 mb-3" role="tablist">
        {d.years.map((v, i) => (
          <button key={v.fy} type="button" role="tab" aria-selected={i === yi}
            onClick={() => { setYi(i); setMi(null) }}
            className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
            style={{ borderColor: i === yi ? 'var(--text-secondary)' : 'var(--grid)',
              color: i === yi ? 'var(--text-primary)' : 'var(--text-muted)',
              background: i === yi ? 'var(--surface-2)' : 'transparent', fontWeight: i === yi ? 600 : 400 }}>
            {v.fy}</button>
        ))}
      </div>
      <p className="text-[13px] mb-2 flex flex-wrap gap-x-4 gap-y-1" style={secondary}>
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm mr-1 align-middle" style={{ background: IN }} />
          {d.text.in} <b style={{ color: 'var(--text-primary)' }}>{y.t_in}</b></span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm mr-1 align-middle" style={{ background: OUT }} />
          {d.text.out} <b style={{ color: 'var(--text-primary)' }}>{y.t_out}</b></span>
        <span>{d.text.close} <b style={{ color: 'var(--text-primary)' }}>{y.t_close}</b></span>
      </p>
      <div className="grid grid-cols-12 gap-[3px] sm:gap-1.5">
        {y.months.map((m, i) => {
          const hin = Math.max(m.in, 0) / d.max * H, hout = Math.max(m.out, 0) / d.max * H
          const on = i === mi
          return (
            <button key={m.m} type="button" onClick={() => setMi(on ? null : i)} aria-pressed={on}
              aria-label={`${m.m}: ${d.text.in} ${m.t_in}, ${d.text.out} ${m.t_out}`}
              className="flex flex-col items-stretch rounded-sm"
              style={{ background: on ? 'var(--surface-2)' : 'transparent' }}>
              <div className="flex items-end justify-center" style={{ height: H }}>
                <div className="w-full max-w-[22px] rounded-t-sm" style={{ height: hin, background: IN }} />
              </div>
              <div style={{ borderTop: '1px solid var(--text-muted)' }} />
              <div className="flex items-start justify-center" style={{ height: H }}>
                <div className="w-full max-w-[22px] rounded-b-sm" style={{ height: hout, background: OUT }} />
              </div>
              <span className="text-[10.5px] sm:text-[11.5px] text-center" style={on ? secondary : muted}>{m.m}</span>
            </button>)
        })}
      </div>
      <div className="mt-3 text-[13.5px]">
        {!sel && <p style={muted}>{d.text.pick}</p>}
        {sel && (<>
          <p className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            {sel.m} {y.fy}: {d.text.in} {sel.t_in} · {d.text.out} {sel.t_out}</p>
          {sel.pays.length + sel.ins.length === 0 && <p style={muted}>{d.text.none}</p>}
          {([[d.text.ins, sel.ins, IN], [d.text.pays, sel.pays, OUT]] as [string, Pay[], string][])
            .filter(([, xs]) => xs.length > 0).map(([head, xs, colour]) => (
            <div key={head} className="mt-2">
              <p className="text-[11.5px] uppercase tracking-wide" style={{ color: colour }}>{head}</p>
              <ul className="divide-y" style={{ borderColor: 'var(--grid)' }}>
                {xs.map((p, j) => (
                  <li key={j} className="py-1.5 grid grid-cols-[1fr_auto] gap-x-3" style={{ borderColor: 'var(--grid)' }}>
                    <span className="min-w-0">
                      <span style={{ color: 'var(--text-primary)' }}>{p.who}</span>
                      <span className="block text-[12.5px] break-words" style={muted}>{p.d} · {p.what}</span>
                    </span>
                    <span className="tabular-nums" style={{ color: 'var(--text-primary)' }}>{p.amt}</span>
                  </li>))}
              </ul>
            </div>))}
        </>)}
      </div>
    </div>)
}
