import { useState } from 'react'
import { MODEL } from '../model/engine'

/** Every rate this project knows about, with the year it applies to and who set it.
 *
 *  Reference, not argument. It exists because of one bug: FY26 athletic fees were priced
 *  at $250 a season for months when the district charged $325 — not a wrong number, a
 *  right number from the wrong year, taken from a schedule that states its rates and never
 *  states which year they cover. Nothing caught it, because a rate with no date attached
 *  looks exactly like a rate with the right date attached.
 *
 *  So the page shows the year, the source and the status for every rate, including the
 *  ones we do not use and the ones we cannot state at all. A fee the town charges and does
 *  not publish is a finding, not a blank. */

const R = MODEL.rateRegister

type Row = (typeof R.rows)[number]

/** The high school full-pay athletic fee in a given year, from the register itself.
 *
 *  Used so the sentence describing the mistake this page exists to prevent cannot itself
 *  go stale. It said "31% of modelled fee revenue" for a while, which was true of the
 *  model before the fee was corrected and of nothing afterwards — the exact failure this
 *  register is for. */
function hsFee(fy: number): number | null {
  const row = R.rows.find((r: Row) => r.category === 'athletic_fee' && r.unit === 'HS'
    && r.item === 'full_pay' && r.fy === fy)
  return row?.value ?? null
}
const MODELLED_FEE = hsFee(2025)
const ACTUAL_FEE = hsFee(2026)
const UNDERSTATED = MODELLED_FEE && ACTUAL_FEE
  ? Math.round((ACTUAL_FEE / MODELLED_FEE - 1) * 100) : null

const CATEGORY: Record<string, { label: string; blurb: string }> = {
  athletic_fee: {
    label: 'Athletic user fees',
    blurb: 'Per student, per sport, per season. High school and middle school schedules '
      + 'are separate and do not combine toward the sibling discount.',
  },
  bus_fee: {
    label: 'Bus fees — getting to school',
    blurb: 'Per family, per year, for regular transportation to school. Not athletics: '
      + 'travel to games is paid by the athletics revolving fund. A bus fee nets down the '
      + 'general education transportation line, so that line can fall without any cost '
      + 'falling.',
  },
  contract_cola: {
    label: 'Collective bargaining — cost-of-living adjustments',
    blurb: 'The percentage added to each salary scale, by year. Steps and lanes move on '
      + 'top of these, so a unit’s payroll grows faster than its COLA.',
  },
  facilities_fee: { label: 'Facilities use fees', blurb: 'Charged for use of school buildings and grounds.' },
  activity_fee: { label: 'Student activity fees', blurb: 'Proposed alongside the athletics increase.' },
  other_fee: {
    label: 'Other fees the district charges',
    blurb: 'Listed by the district’s own payment portal. The portal renders in JavaScript '
      + 'and serves no amounts to a plain fetch, so this establishes that each fee exists '
      + 'and nothing about what it costs.',
  },
}

const STATUS: Record<string, { label: string; tone: string }> = {
  verified:      { label: 'verified',      tone: 'var(--status-good)' },
  recorded:      { label: 'recorded',      tone: 'var(--text-secondary)' },
  reported:      { label: 'reported',      tone: 'var(--status-warning)' },
  not_published: { label: 'not published', tone: 'var(--status-bad)' },
  not_adopted:   { label: 'not adopted',   tone: 'var(--text-muted)' },
}

const TH_L = 'text-left font-bold uppercase tracking-widest text-[10px] pb-1'
const TH_R = 'text-right font-bold uppercase tracking-widest text-[10px] pb-1 pl-3'

function money(r: Row) {
  if (r.value === null) return '—'
  if (r.valueType === 'percent') return `${r.value}%`
  if (r.value === 0) return 'free'
  return `$${r.value.toLocaleString(undefined, {
    minimumFractionDigits: r.value % 1 ? 2 : 0, maximumFractionDigits: 2 })}`
}

function Group({ cat, rows }: { cat: string; rows: Row[] }) {
  const meta = CATEGORY[cat] ?? { label: cat, blurb: '' }
  const years = [...new Set(rows.map(r => r.fy))]
    .sort((a, b) => ((a as number) ?? 0) - ((b as number) ?? 0))
  return (
    <section className="mb-12">
      <h2 className="text-2xl font-bold tracking-tight mb-1">{meta.label}</h2>
      <p className="text-[15px] leading-relaxed max-w-2xl mb-4"
        style={{ color: 'var(--text-secondary)' }}>{meta.blurb}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>FY</th>
              <th className={TH_L + ' pl-3'}>Who</th>
              <th className={TH_L + ' pl-3'}>What</th>
              <th className={TH_R}>Rate</th>
              <th className={TH_L + ' pl-3'}>Set on</th>
              <th className={TH_L + ' pl-3'}>Status</th>
              <th className={TH_L + ' pl-3'}>Source</th>
            </tr>
          </thead>
          <tbody>
            {years.flatMap(y => rows.filter(r => r.fy === y).map((r, i) => (
              <tr key={`${y}-${r.unit}-${r.item}-${i}`} className="border-t"
                style={{ borderColor: 'var(--surface-3)' }}>
                <td className="py-1.5 whitespace-nowrap font-semibold">
                  {r.fy ? `FY${String(r.fy).slice(2)}` : '—'}
                </td>
                <td className="py-1.5 pl-3">{r.unit}</td>
                <td className="py-1.5 pl-3">{r.item.replace(/_/g, ' ')}</td>
                <td className="py-1.5 pl-3 text-right whitespace-nowrap tnum">{money(r)}</td>
                <td className="py-1.5 pl-3 whitespace-nowrap"
                  style={{ color: 'var(--text-secondary)' }}>{r.setOn || '—'}</td>
                <td className="py-1.5 pl-3 whitespace-nowrap font-semibold"
                  style={{ color: STATUS[r.status]?.tone }}>
                  {STATUS[r.status]?.label ?? r.status}
                </td>
                <td className="py-1.5 pl-3 max-w-[22rem]"
                  style={{ color: 'var(--text-secondary)' }}>{r.source}</td>
              </tr>
            )))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export function Rates() {
  const [onlyGaps, setOnlyGaps] = useState(false)
  const rows: Row[] = onlyGaps
    ? R.rows.filter((r: Row) => r.status === 'not_published' || r.status === 'not_adopted')
    : R.rows
  const cats: string[] = [...new Set(rows.map((r: Row) => r.category as string))]

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>Reference, not argument</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Rates, fees and contracts
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Every rate this analysis knows about, with <strong>the fiscal year it applies to,
        the document that set it, and the date it was set</strong>. Nothing here is a
        projection.
      </p>
      <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        It exists because of one mistake. Athletic fees for FY26 were modelled at{' '}
        ${MODELLED_FEE} a season when the district had voted ${ACTUAL_FEE}
        {UNDERSTATED ? ` — understating the rate by ${UNDERSTATED}%` : ''}. Not a wrong
        number, but a right number from the wrong year, taken from a fee schedule that
        states its rates and never states which year they cover. It went unnoticed because
        a rate with no date attached looks exactly like a rate with the right date attached.
        Everything below carries its year.
      </p>

      <div className="flex gap-5 flex-wrap items-center mt-8 mb-6">
        {(Object.entries(R.counts) as [string, number][]).sort().map(([k, n]) => (
          <span key={k} className="text-[13px]">
            <strong className="tnum" style={{ color: STATUS[k]?.tone }}>{n}</strong>{' '}
            <span style={{ color: 'var(--text-secondary)' }}>{STATUS[k]?.label ?? k}</span>
          </span>
        ))}
        <button onClick={() => setOnlyGaps(v => !v)}
          className="ml-auto text-xs font-semibold px-3 py-2 rounded-md"
          style={{ background: onlyGaps ? 'var(--series-cost)' : 'var(--surface-3)',
                   color: onlyGaps ? '#fff' : 'var(--text-primary)' }}>
          {onlyGaps ? 'Show every rate' : 'Show only what we cannot state'}
        </button>
      </div>

      <dl className="card p-4 mb-10 max-w-2xl text-[13px] leading-relaxed"
        style={{ color: 'var(--text-secondary)' }}>
        {(Object.entries(R.statusMeaning) as [string, string][]).map(([k, v]) => (
          <div key={k} className="flex gap-3 py-0.5">
            <dt className="shrink-0 w-[7.5rem] font-semibold"
              style={{ color: STATUS[k]?.tone }}>{STATUS[k]?.label ?? k}</dt>
            <dd className="m-0">{v}</dd>
          </div>
        ))}
      </dl>

      {cats.map(c => (
        <Group key={c} cat={c} rows={rows.filter((r: Row) => r.category === c)} />
      ))}

      <p className="text-[13px] leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        The whole register is published as
        {' '}<a href="https://lunenburgbudgetproject.org/docs/data/rate-register.csv">rate-register.csv</a>, with the athletic
        fee detail in{' '}
        <a href="https://lunenburgbudgetproject.org/docs/data/athletic-fee-schedule.csv">athletic-fee-schedule.csv</a>. Every
        row carries the file and the cell or quotation it rests on.
      </p>
    </div>
  )
}
