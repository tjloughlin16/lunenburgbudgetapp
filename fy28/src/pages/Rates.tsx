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
  verified:      { label: 'verified',      tone: 'var(--ok, #2f7d4f)' },
  recorded:      { label: 'recorded',      tone: 'var(--text-secondary)' },
  reported:      { label: 'reported',      tone: 'var(--warn, #a8730a)' },
  not_published: { label: 'not published', tone: 'var(--bad, #a03232)' },
  not_adopted:   { label: 'not adopted',   tone: 'var(--text-secondary)' },
}

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
    <section style={{ marginBottom: '2.5rem' }}>
      <h3 style={{ margin: '0 0 .25rem' }}>{meta.label}</h3>
      <p style={{ margin: '0 0 .75rem', color: 'var(--text-secondary)', maxWidth: '46rem' }}>
        {meta.blurb}
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '.92rem' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th style={{ padding: '.4rem .6rem .4rem 0' }}>FY</th>
              <th style={{ padding: '.4rem .6rem' }}>Who</th>
              <th style={{ padding: '.4rem .6rem' }}>What</th>
              <th style={{ padding: '.4rem .6rem', textAlign: 'right' }}>Rate</th>
              <th style={{ padding: '.4rem .6rem' }}>Set on</th>
              <th style={{ padding: '.4rem .6rem' }}>Status</th>
              <th style={{ padding: '.4rem 0 .4rem .6rem' }}>Source</th>
            </tr>
          </thead>
          <tbody>
            {years.flatMap(y => rows.filter(r => r.fy === y).map((r, i) => (
              <tr key={`${y}-${r.unit}-${r.item}-${i}`}
                  style={{ borderBottom: '1px solid var(--border-subtle, rgba(128,128,128,.18))' }}>
                <td style={{ padding: '.35rem .6rem .35rem 0', whiteSpace: 'nowrap' }}>
                  {r.fy ? `FY${String(r.fy).slice(2)}` : '—'}
                </td>
                <td style={{ padding: '.35rem .6rem' }}>{r.unit}</td>
                <td style={{ padding: '.35rem .6rem' }}>{r.item.replace(/_/g, ' ')}</td>
                <td style={{ padding: '.35rem .6rem', textAlign: 'right', whiteSpace: 'nowrap',
                             fontVariantNumeric: 'tabular-nums' }}>
                  {money(r)}
                </td>
                <td style={{ padding: '.35rem .6rem', whiteSpace: 'nowrap',
                             color: 'var(--text-secondary)' }}>{r.setOn || '—'}</td>
                <td style={{ padding: '.35rem .6rem', whiteSpace: 'nowrap',
                             color: STATUS[r.status]?.tone }}>
                  {STATUS[r.status]?.label ?? r.status}
                </td>
                <td style={{ padding: '.35rem 0 .35rem .6rem', color: 'var(--text-secondary)',
                             maxWidth: '22rem' }}>{r.source}</td>
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
    <div style={{ padding: '1.5rem 0 4rem' }}>
      <h2 style={{ marginTop: 0 }}>Rates, fees and contracts</h2>
      <p style={{ maxWidth: '46rem' }}>
        Every rate this analysis knows about, with <strong>the fiscal year it applies to,
        the document that set it, and the date it was set</strong>. Reference, not argument —
        nothing here is a projection.
      </p>
      <p style={{ maxWidth: '46rem', color: 'var(--text-secondary)' }}>
        It exists because of one mistake. Athletic fees for FY26 were modelled at $250 a
        season when the district had voted $325. Not a wrong number — a right number from
        the wrong year, taken from a fee schedule that states its rates and never states
        which year they cover. It cost 31% of modelled fee revenue and went unnoticed,
        because a rate with no date attached looks exactly like a rate with the right date
        attached. Everything below carries its year.
      </p>

      <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', alignItems: 'center',
                    margin: '1.25rem 0 2rem' }}>
        {(Object.entries(R.counts) as [string, number][]).sort().map(([k, n]) => (
          <span key={k} style={{ fontSize: '.9rem' }}>
            <strong style={{ color: STATUS[k]?.tone }}>{n}</strong>{' '}
            <span style={{ color: 'var(--text-secondary)' }}>{STATUS[k]?.label ?? k}</span>
          </span>
        ))}
        <button onClick={() => setOnlyGaps(v => !v)}
                style={{ marginLeft: 'auto', padding: '.35rem .7rem', cursor: 'pointer',
                         border: '1px solid var(--border)', borderRadius: '.35rem',
                         background: onlyGaps ? 'var(--surface-3)' : 'transparent',
                         color: 'inherit' }}>
          {onlyGaps ? 'Show every rate' : 'Show only what we cannot state'}
        </button>
      </div>

      <dl style={{ margin: '0 0 2.5rem', fontSize: '.9rem', color: 'var(--text-secondary)',
                   maxWidth: '46rem' }}>
        {(Object.entries(R.statusMeaning) as [string, string][]).map(([k, v]) => (
          <div key={k} style={{ display: 'flex', gap: '.6rem', marginBottom: '.3rem' }}>
            <dt style={{ minWidth: '7.5rem', color: STATUS[k]?.tone }}>
              {STATUS[k]?.label ?? k}
            </dt>
            <dd style={{ margin: 0 }}>{v}</dd>
          </div>
        ))}
      </dl>

      {cats.map(c => (
        <Group key={c} cat={c} rows={rows.filter((r: Row) => r.category === c)} />
      ))}

      <p style={{ maxWidth: '46rem', color: 'var(--text-secondary)', fontSize: '.9rem' }}>
        The whole register is published as
        {' '}<a href="/docs/data/rate-register.csv">rate-register.csv</a>, with the athletic
        fee detail in{' '}
        <a href="/docs/data/athletic-fee-schedule.csv">athletic-fee-schedule.csv</a>. Every
        row carries the file and the cell or quotation it rests on.
      </p>
    </div>
  )
}
