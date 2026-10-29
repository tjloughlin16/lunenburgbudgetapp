/** MONEY IN, MONEY OUT (fy-breakdown). TJ, 29 October 2026, the top priority: "if the school
 *  received circuit breaker money, or idea grant money, or fee money, or whatever, and didnt spend
 *  it, we need to show total revenue and total unspent revenue, overall and on a per-fund basis ...
 *  And the year over year change of that will be important".
 *
 *  One year, the page's. Every fund other than the school general fund, by who paid, the largest
 *  difference first: received, moved between funds, spent, received less spent, the balance at
 *  30 June, and received less spent against the year before. A payer opens on its funds, each
 *  linking to its page. Every figure is formatted by scripts/build_fy_breakdown.py (flows_data). */
import { Fragment, useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'
import { PAYER } from './fy-shared'
import { itemHrefs, useItemIndex, withYear } from './fy-items'

type Pack = { n: { received: number; moved: number; spent: number; net: number; balance: number | null; change: number | null }
  t: { received: string; moved: string; spent: string; net: string; balance: string; known: string; change: string }; unknown: number }
type Fund = Pack & { code: string; name: string }
type Group = Pack & { id: string; label: string; funds: Fund[] }
type Year = { fy: string; open: boolean; total: Pack; groups: Group[]; n_funds: number }
type Data = { years: Year[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }
const link = { color: 'var(--link, var(--thread-2))' }

export default function FyFundFlows({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const href = itemHrefs(useItemIndex())
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const moved = y.groups.some(g => g.t.moved)

  const balance = (p: Pack, n: number) => p.t.balance
    || (p.t.known ? <span title={`${t.known_part}`}>{p.t.known}<span className="block text-[11px]" style={muted}>{t.unknown_bal} {p.unknown} {t.unknown_bal_tail}</span></span>
      : <span style={muted} title={`${t.unknown_bal} ${p.unknown} / ${n}`}>—</span>)
  const cells = (p: Pack, n: number, strong = false) => <>
    <td className="px-2 py-1.5 text-right">{p.t.received}</td>
    {moved ? <td className="px-2 py-1.5 text-right" style={muted}>{p.t.moved}</td> : null}
    <td className="px-2 py-1.5 text-right">{p.t.spent}</td>
    <td className={`px-2 py-1.5 text-right ${strong ? 'font-semibold' : ''}`}>{p.t.net}</td>
    <td className="px-2 py-1.5 text-right">{balance(p, n)}</td>
    <td className="px-2 py-1.5 text-right" style={muted}>{p.t.change || '—'}</td>
  </>
  const th = (label: string, means: string) => <th className="px-2 py-1.5 text-right font-semibold align-bottom" title={means}>{label}</th>

  return (
    <figure aria-label={alt}>
      {y.open ? <p className="text-[12.5px] mb-2" style={muted}>{y.fy}: {t.open}</p> : null}
      <div className="overflow-x-auto">
        <table className="w-full text-[13px] tabular-nums border-collapse min-w-[680px]">
          <thead>
            <tr className="border-b text-[12px]" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              <th className="px-2 py-1.5 text-left font-semibold align-bottom">{t.h_group}</th>
              {th(t.h_received, t.means_received)}
              {moved ? th(t.h_moved, t.means_moved) : null}
              {th(t.h_spent, t.means_spent)}
              {th(t.h_net, t.means_net)}
              {th(t.h_balance, t.means_balance)}
              {th(t.h_change, t.means_change)}
            </tr>
          </thead>
          <tbody>
            {y.groups.map(g => (
              <Fragment key={g.id}>
                <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                  <td className="px-2 py-1.5 text-left">
                    <button type="button" onClick={() => setOpen(o => ({ ...o, [g.id]: !o[g.id] }))} aria-expanded={!!open[g.id]}
                      className="inline-flex items-center gap-1.5 text-left">
                      <span className="inline-block w-3 text-[10px]" style={muted}>{open[g.id] ? '▼' : '▶'}</span>
                      <span className="inline-block w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: PAYER[g.id] }} />
                      <span className="font-semibold">{g.label}</span>
                      <span className="text-[11.5px]" style={muted}>{g.funds.length} {g.funds.length === 1 ? t.fund : t.funds}</span>
                    </button></td>
                  {cells(g, g.funds.length, true)}
                </tr>
                {open[g.id] ? g.funds.map(f => {
                  const h = href.fund(f.code)
                  return (
                    <tr key={f.code} className="border-b text-[12.5px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)' }}>
                      <td className="pl-9 pr-2 py-1 text-left">
                        {h ? <a href={withYear(h, y.fy)} className="underline" style={link}>{f.name}</a> : f.name}
                        <span className="ml-1.5 text-[11px]" style={muted}>{f.code}</span></td>
                      {cells(f, 1)}
                    </tr>)
                }) : null}
              </Fragment>))}
            <tr className="border-t-2" style={{ borderColor: 'var(--text-secondary)' }}>
              <td className="px-2 py-1.5 text-left font-semibold">{t.all}
                <span className="ml-1.5 text-[11.5px] font-normal" style={muted}>{y.n_funds} {t.funds}</span></td>
              {cells(y.total, y.n_funds, true)}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-[12px] mt-2 max-w-3xl" style={muted}>{t.left_out}</p>
    </figure>)
}
