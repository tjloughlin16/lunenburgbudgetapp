import { useEffect, useState } from 'react'
import { MODEL, usd } from '../model/engine'

const H = MODEL.health
const yr = (monthly: number) => monthly * 12

/** What a plan change actually costs the person holding the plan. */
export function HealthInsurance({ empShare, setEmpShare, movers, setMovers, onSaving }: {
  empShare: number; setEmpShare: (n: number) => void
  movers: number; setMovers: (n: number) => void
  onSaving: (n: number) => void
}) {
  const [fromId, setFromId] = useState('bce')
  const [toId, setToId] = useState('bs')

  const famShare = H.familyShare
  const enrolled = Object.values(H.enrolment).reduce((a, b) => a + b, 0)
  const totalPremium = H.plans.reduce((s, p) => {
    const n = H.enrolment[p.id] ?? 0
    return s + yr(p.family) * n * famShare + yr(p.individual) * n * (1 - famShare)
  }, 0)

  const shift = empShare - (1 - H.townShare)
  const splitSaving = totalPremium * shift

  const from = H.plans.find(p => p.id === fromId)!
  const to = H.plans.find(p => p.id === toId)!
  const migTotal = (yr(from.family) - yr(to.family)) * movers * famShare
    + (yr(from.individual) - yr(to.individual)) * movers * (1 - famShare)
  const migTown = migTotal * H.townShare

  const gross = splitSaving + migTown
  const mitigated = gross * 0.75   // c.32B §§21-23: 25% of first-year savings to employees

  // Only the migration half is reported up: the split half is the health_design lever,
  // which the workbench already counts. Reporting both would double it.
  const migrationKept = migTown * 0.75
  useEffect(() => { onSaving(migrationKept) }, [migrationKept, onSaving])

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* ---- lever 1: who pays what share ---- */}
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">Shift the premium split</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          The Town pays {(H.townShare * 100).toFixed(0)}% today. Every dollar the district
          saves here is a dollar an employee pays. This is the same control as the
          &ldquo;employee share&rdquo; lever on the{' '}
          <a href="#levers" className="underline">Close the gap</a> tab &mdash; move either
          one and the projection, the cut line and the running total all follow.
        </p>

        <div className="flex items-baseline justify-between mb-1">
          <label htmlFor="empshare" className="text-[13px] font-medium">
            Employee share of the premium
          </label>
          <span className="flex items-baseline gap-2">
            <span className="text-xl font-bold tnum">{(empShare * 100).toFixed(0)}%</span>
            {empShare !== 1 - H.townShare && (
              <button onClick={() => setEmpShare(1 - H.townShare)}
                className="text-[10px] font-semibold underline"
                style={{ color: 'var(--text-secondary)' }}>
                reset
              </button>
            )}
          </span>
        </div>
        <input id="empshare" type="range" min={1 - H.townShare} max={0.40} step={0.01}
          value={empShare} onChange={e => setEmpShare(Number(e.target.value))}
          className="w-full" />
        <div className="flex justify-between text-[10px] mb-4"
          style={{ color: 'var(--text-muted)' }}>
          <span>today {(100 - H.townShare * 100).toFixed(0)}%</span><span>40%</span>
        </div>

        <p className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>District saves</p>
        <p className="text-3xl font-bold tnum leading-none mb-4"
          style={{ color: splitSaving > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
          {usd(splitSaving)}
        </p>

        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--status-serious)' }}>What it costs each employee, per year</p>
        <div className="overflow-x-auto">
          <table className="stack w-full text-xs tnum">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="font-semibold py-1">Plan</th>
                <th className="font-semibold py-1 text-right">Family now</th>
                <th className="font-semibold py-1 text-right">Family after</th>
                <th className="font-semibold py-1 text-right">Change</th>
              </tr>
            </thead>
            <tbody>
              {H.plans.map(p => {
                const now = yr(p.family) * (1 - H.townShare)
                const after = yr(p.family) * empShare
                return (
                  <tr key={p.id} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                    <td className="rowhead py-1.5">{p.name}</td>
                    <td data-label="Family now" className="py-1.5 text-right">{usd(now)}</td>
                    <td data-label="Family after"
                      className="py-1.5 text-right font-semibold">{usd(after)}</td>
                    <td data-label="Change" className="py-1.5 text-right font-bold"
                      style={{ color: after > now ? 'var(--status-critical)' : 'var(--text-muted)' }}>
                      {after > now ? '+' : ''}{usd(after - now)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          Individual-tier employees pay roughly 38% of the family figures. A single point of
          shift is about {usd(totalPremium * 0.01)} to the district.
        </p>
      </div>

      {/* ---- lever 2: move people to cheaper plans ---- */}
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">Move employees to a cheaper plan</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          The four plans differ by {usd(yr(H.plans[0].family) - yr(H.plans[2].family))} a
          year at the family tier. Cheaper plans mean narrower networks or higher
          deductibles &mdash; a real change in what care costs an employee.
        </p>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label htmlFor="from" className="text-[11px] block mb-1"
              style={{ color: 'var(--text-muted)' }}>From</label>
            <select id="from" value={fromId} onChange={e => setFromId(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg border text-[12px]"
              style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)',
                       color: 'var(--text-primary)' }}>
              {H.plans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="to" className="text-[11px] block mb-1"
              style={{ color: 'var(--text-muted)' }}>To</label>
            <select id="to" value={toId} onChange={e => setToId(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg border text-[12px]"
              style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)',
                       color: 'var(--text-primary)' }}>
              {H.plans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>

        <div className="flex items-baseline justify-between mb-1">
          <label htmlFor="movers" className="text-[13px] font-medium">Employees moved</label>
          <span className="flex items-baseline gap-2">
            <span className="text-xl font-bold tnum">{movers}</span>
            {movers !== 0 && (
              <button onClick={() => setMovers(0)}
                className="text-[10px] font-semibold underline"
                style={{ color: 'var(--text-secondary)' }}>
                reset
              </button>
            )}
          </span>
        </div>
        <input id="movers" type="range" min={0} max={H.enrolment[fromId] ?? 50} step={1}
          value={Math.min(movers, H.enrolment[fromId] ?? 50)}
          onChange={e => setMovers(Number(e.target.value))} className="w-full mb-1" />
        <p className="text-[10px] mb-4" style={{ color: 'var(--text-muted)' }}>
          about {H.enrolment[fromId] ?? 0} are on {from.name} today (our estimate)
        </p>

        <p className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>District saves</p>
        <p className="text-3xl font-bold tnum leading-none mb-3"
          style={{ color: migTown > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
          {usd(migTown)}
        </p>

        <dl className="text-[12px] space-y-1 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <Row k={`${from.name} — deductible`} v={from.deductible} />
          <Row k={`${to.name} — deductible`} v={to.deductible} />
          <Row k="Network change" v={`${from.network} → ${to.network}`} />
          <Row k="Employee premium change, family"
            v={usd(yr(to.family) * (1 - H.townShare) - yr(from.family) * (1 - H.townShare))} />
        </dl>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          A cheaper premium can still cost an employee more overall: moving to Access Blue
          Saver trades a $500 deductible for $2,000 individual / $4,000 family.
        </p>
      </div>

      {/* ---- the catch ---- */}
      <div className="card p-5 lg:col-span-2" style={{ borderColor: 'var(--status-serious)' }}>
        <div className="grid gap-4 sm:grid-cols-3 mb-4">
          <Fig v={usd(gross)} k="Headline saving" s="both levers combined" />
          <Fig v={usd(mitigated)} k="Year-one saving" s="after the 25% owed back to employees"
            accent />
          <Fig v={`${enrolled}`} k="Employees affected"
            s={`of about 253 staff; premiums rose ${(H.rateIncrease * 100).toFixed(2)}% for FY27`} />
        </div>
        <ul className="space-y-2 text-[12px] leading-relaxed list-disc pl-4"
          style={{ color: 'var(--text-secondary)' }}>
          {H.constraints.map(c => <li key={c.slice(0, 24)}>{c}</li>)}
        </ul>
      </div>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="min-w-0" style={{ color: 'var(--text-secondary)' }}>{k}</dt>
      <dd className="font-semibold text-right">{v}</dd>
    </div>
  )
}

function Fig({ v, k, s, accent }: { v: string; k: string; s: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-2xl font-bold tnum leading-none"
        style={{ color: accent ? 'var(--status-good)' : 'var(--text-primary)' }}>{v}</p>
      <p className="text-[12px] font-semibold mt-1">{k}</p>
      <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{s}</p>
    </div>
  )
}
