/** THE BIGGEST CHANGES FROM LAST YEAR (fy-breakdown). TJ, 29 October 2026: "the hockeystick
 *  spending curve in collaborative tuition fund year over year needs to be called out ... a
 *  specific table for 'big changes' (both biggest spend changes, biggest budget changes, or
 *  biggest unspent changes)".
 *
 *  The page's year against the one before: three short lists -- what a line cost from every fund,
 *  its final budget, what was left -- each ranked by DOLLARS, both years, the change, and a
 *  percentage only where the year before was big enough for one to mean something (the generator
 *  decides, scripts/build_fy_breakdown.py big_changes). A line opens on its page. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'
import { itemHrefs, useItemIndex, withYear } from './fy-items'

type Change = { account: string; name: string; cat: string; n: number; state: '' | 'new' | 'gone'
  t: { was: string; now: string; chg: string; pct: string } }
type List = { id: string; label: string; rows: Change[]; n_changed: number }
type Year = { fy: string; prev: string; lists: List[] }
type Data = { years: Year[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }
const link = { color: 'var(--link, var(--thread-2))' }

export default function FyBigChanges({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const all = useMemo(() => d.years.map(v => v.fy), [d])
  // the picker's years include the first, which has no year before it
  const [fy] = useFyYear(all)
  const y = d.years.find(v => v.fy === fy)
  const href = itemHrefs(useItemIndex())
  if (!y) return <p className="text-[13px]" style={muted}>{t.none}</p>
  return (
    <figure aria-label={alt} className="space-y-6">
      {y.lists.map(L => (
        <div key={L.id}>
          <p className="text-[14px] font-semibold">{L.label}
            <span className="ml-2 text-[12px] font-normal" style={muted}>{L.rows.length} {t.of} {L.n_changed} {t.changed}</span></p>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] tabular-nums border-collapse min-w-[560px]">
              <thead>
                <tr className="border-b text-[12px]" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                  <th className="px-2 py-1 text-left font-semibold" />
                  <th className="px-2 py-1 text-right font-semibold">{y.prev}</th>
                  <th className="px-2 py-1 text-right font-semibold">{y.fy}</th>
                  <th className="px-2 py-1 text-right font-semibold">{t.chg}</th>
                  <th className="px-2 py-1 text-right font-semibold">{t.pct}</th>
                </tr>
              </thead>
              <tbody>
                {L.rows.map(r => {
                  const h = href.line(r.account)
                  return (
                    <tr key={r.account} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                      <td className="px-2 py-1.5 text-left">
                        {h ? <a href={withYear(h, y.fy)} className="underline" style={link}>{r.name}</a> : r.name}
                        <span className="block text-[11.5px]" style={muted}>{r.cat}{r.state ? ` · ${r.state === 'new' ? t.new : t.gone}` : ''}</span></td>
                      <td className="px-2 py-1.5 text-right" style={muted}>{r.t.was}</td>
                      <td className="px-2 py-1.5 text-right">{r.t.now}</td>
                      <td className="px-2 py-1.5 text-right font-semibold">{r.t.chg}</td>
                      <td className="px-2 py-1.5 text-right" style={muted}>{r.t.pct || '—'}</td>
                    </tr>)
                })}
              </tbody>
            </table>
          </div>
        </div>))}
    </figure>)
}
