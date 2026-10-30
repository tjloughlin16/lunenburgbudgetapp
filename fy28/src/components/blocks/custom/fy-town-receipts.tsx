/** SCHOOL MONEY THAT GOES TO THE TOWN (fy-breakdown). TJ, 29 October 2026: "i also want the
 *  preschool money to go into the FY breakdown page ... its own section to show the additional
 *  funds." Three receipts the schools generate -- preschool tuition, student parking fees, a school
 *  medical reimbursement -- that the Town books in its own general fund, for the page's year: a bar
 *  for what was received, a mark at the Town's estimate, or the reason the year is not held. Every
 *  figure is formatted by scripts/build_fy_breakdown.py (town_receipts_data). */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

type Row = { id: string; name: string; what: string; received: number | null; estimate: number | null
  t: { received: string; estimate: string }; src: string; href: string }
type Year = { fy: string; rows: Row[]; why: string
  together: { received: number | null; estimate: number | null; t: { received: string; estimate: string }; src: string; href: string } | null }
type Data = { years: Year[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }
const COLOURS: Record<string, string> = { preschool: 'var(--thread-1)', parking: 'var(--thread-2)', medical: 'var(--thread-5)' }

export default function FyTownReceipts({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const max = Math.max(1, ...d.years.flatMap(v => v.rows.flatMap(r => [r.received ?? 0, r.estimate ?? 0])))
  const any = y.rows.some(r => r.received != null || r.estimate != null)
  return (
    <figure aria-label={alt}>
      <p className="text-[13px] mb-3 max-w-3xl" style={secondary}>{t.read}</p>
      {any ? (
        <div className="space-y-3">
          {y.rows.map(r => (
            <div key={r.id}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-[13px]">
                <span className="font-semibold">{r.name}</span>
                <span className="tabular-nums">{r.received != null ? <>{t.received} <b>{r.t.received}</b></> : <span style={muted}>{t.none}</span>}
                  {r.estimate != null ? <span style={muted}> · {t.estimate} {r.t.estimate}</span> : null}</span>
              </div>
              <div className="relative h-3.5 mt-1" style={{ background: 'var(--grid)' }}>
                {r.received != null ? <div className="absolute inset-y-0 left-0" style={{ width: `${(r.received / max) * 100}%`, background: COLOURS[r.id] ?? 'var(--thread-3)' }} /> : null}
                {r.estimate != null ? <div className="absolute -inset-y-1 w-0.5" style={{ left: `${(r.estimate / max) * 100}%`, background: 'var(--text-primary, currentColor)' }} /> : null}
              </div>
              <p className="text-[12px] mt-0.5" style={muted}>{r.what}{r.href ? <> · <a className="underline" style={link} href={r.href}>{r.src}</a></> : null}</p>
            </div>))}
        </div>) : null}
      {y.together ? (
        <p className="text-[13px] mt-3">
          <span className="font-semibold">{t.together}: </span>
          {y.together.received != null ? <>{t.received} <b className="tabular-nums">{y.together.t.received}</b></> : null}
          {y.together.estimate != null ? <>{t.estimate} <b className="tabular-nums">{y.together.t.estimate}</b></> : null}
          {' · '}<a className="underline" style={link} href={y.together.href}>{y.together.src}</a></p>) : null}
      {y.why ? <p className="text-[13px] mt-2" style={secondary}>{y.why}</p> : null}
      <p className="text-[13px] mt-3 flex flex-wrap gap-x-4 gap-y-1">
        <a className="underline" style={link} href={t.preschool_href}>{t.preschool} →</a>
        <a className="underline" style={link} href={t.fund_href}>{t.fund} →</a></p>
    </figure>)
}
