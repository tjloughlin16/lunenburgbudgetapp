import { useState } from 'react'
import { MODEL, usd } from '../model/engine'
import { FeeCurve, feeRevenue, type CurveArgs } from './FeeCurve'

const A = MODEL.athletics

/** Fee scenarios against the whole athletics program. */
export function AthleticsFees({ fee, setFee }: {
  fee: number; setFee: (n: number) => void
}) {
  const CURRENT = MODEL.currentFees.effectiveAthletic
  const [dropoff, setDropoff] = useState(5)   // % participation lost per $100 of fee
  const [waiver, setWaiver] = useState(12)    // % of athletes granted a hardship waiver
  // Which athletics are we asking the fee to pay for? The adopted budget funds no
  // transportation at all, so "self-funding" against it is a trick question — default to
  // the rung that puts the buses back.
  const [basisId, setBasisId] = useState('travel')
  const basis = A.ladder.find(r => r.id === basisId) ?? A.ladder[0]

  // Only high-school participations are chargeable: middle school teams are unfunded in
  // the adopted budget, so there is no team to charge for.
  const args: CurveArgs = {
    current: CURRENT, payers: A.chargeableParticipations, dropoff, waiver,
    target: basis.total, max: 1400,
  }
  const increase = Math.max(0, fee - CURRENT)
  const retained = Math.max(0, 1 - (increase / 100) * (dropoff / 100))
  const paying = A.chargeableParticipations * retained * (1 - waiver / 100)
  const raised = feeRevenue(fee, args)
  const baseline = feeRevenue(CURRENT, args)
  const newMoney = raised - baseline
  const pctProgram = (raised / basis.total) * 100

  const SCENARIOS = A.ladder.map(r => ({ label: r.label, target: r.total, sub: r.scenario }))
  // Revenue is NOT monotonic in the fee: it rises, peaks, then falls as participation
  // drops away. So scan for the cheapest fee that reaches the target rather than
  // bisecting, and report the peak when no fee reaches it.
  const yieldAt = (f: number) => feeRevenue(f, args)

  let peakFee = 0, peakYield = 0
  for (let f = 0; f <= 3000; f += 5) {
    const y = yieldAt(f)
    if (y > peakYield) { peakYield = y; peakFee = f }
  }
  const feeFor = (target: number) => {
    for (let f = 0; f <= 3000; f += 5) if (yieldAt(f) >= target) return f
    return null
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">Set a fee, see what it raises</h3>

        <p className="text-[12px] mb-2" style={{ color: 'var(--text-secondary)' }}>
          Pay for itself <em>against what?</em> The adopted budget funds no athletic
          transportation at all, so measuring against it flatters the answer.
        </p>
        <div className="flex flex-wrap gap-1 mb-4">
          {A.ladder.map(r => (
            <button key={r.id} onClick={() => setBasisId(r.id)}
              aria-pressed={basisId === r.id}
              className="px-2 py-1 rounded-md text-[11px] font-semibold border text-left"
              style={{
                borderColor: basisId === r.id ? 'var(--series-cost)' : 'var(--grid)',
                background: basisId === r.id ? 'var(--series-cost)' : 'var(--surface-1)',
                color: basisId === r.id ? '#fff' : 'var(--text-secondary)',
              }}>
              {r.label}
              <span className="block font-normal tnum opacity-80">{usd(r.total)}</span>
            </button>
          ))}
        </div>
        <p className="text-[11px] mb-4 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          {basis.sub}{' '}
          <span className="font-semibold">
            {basis.published
              ? `Source: the district's ${basis.scenario} column.`
              : 'Our construction — not a budget the district published.'}
          </span>
        </p>

        <div className="flex items-baseline justify-between mb-1">
          <label htmlFor="ath-fee" className="text-[13px] font-medium">
            Fee per season, per athlete
            <span className="block text-[11px] font-normal" style={{ color: 'var(--text-muted)' }}>
              today: {usd(CURRENT)} blended
            </span>
          </label>
          <span className="flex items-baseline gap-2">
            <span className="text-xl font-bold tnum">{usd(fee)}</span>
            {fee !== CURRENT && (
              <button onClick={() => setFee(CURRENT)}
                className="text-[10px] font-semibold underline"
                style={{ color: 'var(--text-secondary)' }}>
                reset
              </button>
            )}
          </span>
        </div>
        <input id="ath-fee" type="range" min={CURRENT} max={1400} step={5} value={fee}
          onChange={e => setFee(Number(e.target.value))} className="w-full mb-4" />

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="flex items-baseline justify-between mb-1">
              <label htmlFor="ath-drop" className="text-[12px]">Participation lost</label>
              <span className="text-xs font-bold tnum">{dropoff}%<span
                className="font-normal" style={{ color: 'var(--text-muted)' }}>/$100</span></span>
            </div>
            <input id="ath-drop" type="range" min={0} max={20} step={1} value={dropoff}
              onChange={e => setDropoff(Number(e.target.value))} className="w-full" />
          </div>
          <div>
            <div className="flex items-baseline justify-between mb-1">
              <label htmlFor="ath-waiver" className="text-[12px]">Hardship waivers</label>
              <span className="text-xs font-bold tnum">{waiver}%</span>
            </div>
            <input id="ath-waiver" type="range" min={0} max={40} step={1} value={waiver}
              onChange={e => setWaiver(Number(e.target.value))} className="w-full" />
          </div>
        </div>

        {/* --- how much of the athletics budget this covers --- */}
        <div className="pt-4 mt-1 border-t" style={{ borderColor: 'var(--grid)' }}>
          <div className="flex items-baseline justify-between gap-3 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>
              Share of the athletics budget covered
            </span>
            <span className="text-3xl font-bold tnum leading-none"
              style={{ color: pctProgram >= 100 ? 'var(--status-good)'
                : pctProgram >= 50 ? 'var(--status-serious)' : 'var(--status-critical)' }}>
              {pctProgram.toFixed(0)}%
            </span>
          </div>
          <div className="h-4 rounded-full overflow-hidden flex"
            style={{ background: 'var(--surface-3)' }}>
            <div className="h-full"
              style={{ width: `${Math.min(100, (baseline / basis.total) * 100)}%`,
                       background: 'var(--series-cost)' }} />
            <div className="h-full"
              style={{ width: `${Math.min(100 - (baseline / basis.total) * 100,
                                 (newMoney / basis.total) * 100)}%`,
                       background: 'var(--status-good)' }} />
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] mt-1.5"
            style={{ color: 'var(--text-muted)' }}>
            <span>
              <span aria-hidden="true" style={{ color: 'var(--series-cost)' }}>&#9632; </span>
              today&rsquo;s fee {usd(baseline)}
            </span>
            <span>
              <span aria-hidden="true" style={{ color: 'var(--status-good)' }}>&#9632; </span>
              added by the increase {usd(newMoney)}
            </span>
            <span>
              still unfunded {usd(Math.max(0, basis.total - raised))}
            </span>
          </div>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            {usd(raised)} of the {usd(basis.total)} that <strong>{basis.label.toLowerCase()}</strong>{' '}
            costs.{' '}
            {pctProgram >= 100
              ? 'Athletics pays for itself entirely at this fee.'
              : <>The remaining <strong>{usd(basis.total - raised)}</strong> still comes
                out of the school budget &mdash; competing with classrooms.</>}
          </p>
        </div>

        <div className="pt-4 mt-4 border-t space-y-2" style={{ borderColor: 'var(--grid)' }}>
          <Line k="Athletes still playing"
            v={`${Math.round(A.chargeableParticipations * retained).toLocaleString()} of ${A.chargeableParticipations}`} />
          <Line k="Paying after waivers" v={Math.round(paying).toLocaleString()} />
          <Line k="Total raised each year" v={usd(raised)} bold />
          <Line k="New money vs today" v={usd(newMoney)} bold />
        </div>

        <p className="text-[11px] mt-4" style={{ color: 'var(--text-muted)' }}>
          Lunenburg already charges, and raised the fee for 2026-27: $400 for a first
          child, $300 second, $225 third, with a $1,500 family cap &mdash; up from
          $250/$140/$85 and a $475 cap. Blended across the sibling discount that is about{' '}
          {usd(CURRENT)} per participation.
          <strong> Only a further increase above today&rsquo;s fee is new money.</strong>{' '}
          Drop-off and waiver rates are assumptions, not Lunenburg measurements.
        </p>
      </div>

      <div>
        <div className="card p-5 mb-4">
          <h3 className="text-sm font-bold mb-3">What each goal costs a family</h3>
          <ul className="space-y-2.5">
            {SCENARIOS.map(s => {
              const f = feeFor(s.target)
              return (
                <li key={s.label} className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>
                    {s.label}
                    <span className="block text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
                      costs {usd(s.target)} · {s.sub}
                    </span>
                  </span>
                  <span className="text-lg font-bold tnum shrink-0 text-right">
                    {f === null
                      ? <span style={{ color: 'var(--status-critical)' }}>out of reach</span>
                      : usd(f)}
                    <span className="text-[11px] font-normal block"
                      style={{ color: 'var(--text-muted)' }}>
                      {f === null ? 'no fee raises this much' : 'per season'}
                    </span>
                  </span>
                </li>
              )
            })}
          </ul>
          <p className="text-[11px] mt-3 pt-3 border-t" style={{ color: 'var(--text-muted)', borderColor: 'var(--grid)' }}>
            At your current drop-off and waiver settings. Revenue peaks at{' '}
            <strong>{usd(peakFee)} per season</strong>, raising <strong>{usd(peakYield)}</strong>{' '}
            — charge more than that and so many families drop out that the district
            collects <em>less</em>, not more. That ceiling is why full self-funding can be
            out of reach for anything above {usd(A.travel)} — including the full{' '}
            {usd(A.levelService)} programme, even though the flat arithmetic says{' '}
            {usd(A.levelService / A.participations)} would cover it.
          </p>
        </div>

        <div className="card p-5 mb-4">
          <h3 className="text-sm font-bold mb-3">What other districts charge</h3>
          <ul className="space-y-2">
            {MODEL.feeBenchmarks.map(b => (
              <li key={b.district} className="text-[13px]">
                <span className="flex items-baseline justify-between gap-3">
                  <span style={{ fontWeight: b.district === 'Lunenburg' ? 700 : 500 }}>
                    {b.district}{b.local && <span className="ml-1.5 text-[9px] uppercase
                      tracking-widest font-bold" style={{ color: 'var(--text-muted)' }}>local</span>}
                  </span>
                  <span className="font-bold tnum shrink-0">
                    {b.fee === null ? '—' : b.fee === 0 ? 'none' : usd(b.fee)}
                  </span>
                </span>
                <span className="block text-[11px] leading-snug" style={{ color: 'var(--text-muted)' }}>
                  {b.note}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="lg:col-span-2">
        <FeeCurve args={args} fee={fee} label="Athletics: what each fee level actually raises" />
      </div>
    </div>
  )
}

/** Per-sport cost table — the "which sports are expensive" question. */
export function SportTable({ fee }: { fee: number }) {
  const [sort, setSort] = useState<'perAthlete' | 'cost' | 'students' | 'coverage'>('perAthlete')
  const [loaded, setLoaded] = useState(false)

  // Per-sport figures are direct programme costs only. Loading them up spreads the
  // athletic director, trainer, secretary, insurance, dues and transport across sports
  // in proportion to their direct cost.
  const OVERHEAD = A.levelService / A.perSportTotal
  const mult = loaded ? OVERHEAD : 1
  const costOf = (sp: { cost: number }) => sp.cost * mult
  const perAthlete = (sp: { cost: number; students: number }) => costOf(sp) / sp.students
  const coverage = (sp: { cost: number; students: number }) => fee / perAthlete(sp)

  const sports = [...MODEL.sports].sort((a, b) =>
    sort === 'perAthlete' ? perAthlete(b) - perAthlete(a)
      : sort === 'cost' ? b.cost - a.cost
      : sort === 'coverage' ? coverage(a) - coverage(b)
      : b.students - a.students)

  const selfFunding = sports.filter(sp => Math.round(coverage(sp) * 100) >= 100).length

  const H = ({ k, label }: { k: typeof sort; label: string }) => (
    <th className="font-semibold py-1.5 text-right">
      <button onClick={() => setSort(k)}
        style={{ color: sort === k ? 'var(--text-primary)' : 'var(--text-muted)',
                 fontWeight: sort === k ? 700 : 600 }}>{label}</button>
    </th>
  )

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <p className="text-[13px]">
          At <strong>{usd(fee)}</strong> a season,{' '}
          <strong style={{ color: selfFunding > 0 ? 'var(--status-good)' : 'var(--status-critical)' }}>
            {selfFunding} of {sports.length} sports
          </strong>{' '}
          pay for themselves.
        </p>
        <div className="flex gap-1">
          {[[false, 'Direct cost'], [true, 'With overhead']].map(([v, label]) => (
            <button key={String(v)} onClick={() => setLoaded(v as boolean)}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold border"
              style={{
                borderColor: loaded === v ? 'var(--series-cost)' : 'var(--grid)',
                background: loaded === v ? 'var(--series-cost)' : 'var(--surface-1)',
                color: loaded === v ? '#fff' : 'var(--text-secondary)',
              }}>{label as string}</button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs tnum min-w-[560px]">
          <caption className="sr-only">
            Lunenburg athletics: participations and programmatic cost per sport, FY24
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Sport</th>
              <H k="students" label="Athletes" />
              <H k="cost" label="Cost" />
              <H k="perAthlete" label="Per athlete" />
              <H k="coverage" label="Covered by the fee" />
            </tr>
          </thead>
          <tbody>
            {sports.map(s => (
              <tr key={s.name} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5">
                  {s.name}
                  {s.level === 'MS' && <span className="ml-1.5 text-[9px] uppercase
                    tracking-widest font-bold" style={{ color: 'var(--text-muted)' }}>middle</span>}
                </td>
                <td className="py-1.5 text-right">{s.students}</td>
                <td className="py-1.5 text-right">{usd(costOf(s))}</td>
                <td className="py-1.5 text-right font-semibold">{usd(perAthlete(s))}</td>
                <td className="py-1.5 pl-3"><Coverage pct={coverage(s)} /></td>
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
              <td className="py-2">All sports</td>
              <td className="py-2 text-right">{A.participations}</td>
              <td className="py-2 text-right">{usd(A.perSportTotal * mult)}</td>
              <td className="py-2 text-right">
                {usd((A.perSportTotal * mult) / A.participations)}
              </td>
              <td className="py-2 pl-3">
                <Coverage pct={fee / ((A.perSportTotal * mult) / A.participations)} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
        <strong>Covered by the fee</strong> compares the fee you set above against what
        each sport costs per athlete. &ldquo;Direct cost&rdquo; counts only that
        sport&rsquo;s own spending; <strong>&ldquo;With overhead&rdquo;</strong> also
        spreads the athletic director, trainer, secretary, insurance, dues and
        district-wide transport across the sports in proportion to their direct cost, which
        is the fairer test of whether a sport truly pays for itself.
        {' '}FY24 programmatic cost per sport, from the district&rsquo;s own
        &ldquo;Athletic Program Costs by Sport.&rdquo; Athletes are participations, not
        unique students &mdash; a three-sport athlete counts three times, which is also how
        a per-season fee would be charged. These per-sport costs total{' '}
        {usd(MODEL.athletics.perSportTotal)}; the full budgeted program is{' '}
        {usd(MODEL.athletics.levelService)}, the difference being the athletic director,
        trainer, secretary, insurance, dues and district-wide transportation.
      </p>
    </div>
  )
}

function Line({ k, v, bold }: { k: string; v: string; bold?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-[13px]">
      <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
      <span className={`tnum shrink-0 ${bold ? 'font-bold text-base' : ''}`}>{v}</span>
    </div>
  )
}

/** Where the fee money goes — what we could establish, and what we could not. */
export function FeeAccounting() {
  const a = MODEL.feeAccounting
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-3">
          <span aria-hidden="true" style={{ color: 'var(--status-good)' }}>✓ </span>
          What the documents establish
        </h3>
        <ul className="space-y-2.5 text-[13px] leading-relaxed list-disc pl-4"
          style={{ color: 'var(--text-secondary)' }}>
          {a.established.map(x => <li key={x.slice(0, 30)}>{x}</li>)}
        </ul>
      </div>
      <div className="card p-5" style={{ borderColor: 'var(--status-serious)' }}>
        <h3 className="text-sm font-bold mb-3">
          <span aria-hidden="true" style={{ color: 'var(--status-serious)' }}>? </span>
          What we could not settle
        </h3>
        <ul className="space-y-2.5 text-[13px] leading-relaxed list-disc pl-4"
          style={{ color: 'var(--text-secondary)' }}>
          {a.unresolved.map(x => <li key={x.slice(0, 30)}>{x}</li>)}
        </ul>
        <p className="text-[13px] leading-relaxed mt-3 pt-3 border-t font-medium"
          style={{ borderColor: 'var(--grid)' }}>{a.ask}</p>
      </div>
    </div>
  )
}

/** The fee schedule Lunenburg charges today — raised for 2026-27. */
export function CurrentFees() {
  const f = MODEL.currentFees
  const a = f.athletic
  const prior = a.prior
  // Measured against the same basis the fee tool leads with: the teams that survived,
  // able to travel. Quoting a share of level service here would flatter the old fee and
  // contradict the panel directly below.
  const pctOfProgram = Math.round((f.estimatedAthleticRevenue / A.travel) * 100)
  const priorPct = Math.round((f.estimatedPriorAthleticRevenue / A.travel) * 100)

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <h3 className="text-sm font-bold">What Lunenburg charges today</h3>
        <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded"
          style={{ background: 'var(--status-serious)', color: '#fff' }}>
          raised for {a.effectiveFrom}
        </span>
      </div>
      <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
        Source: {a.source}.
      </p>

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>Athletics, per season</p>
          <ul className="space-y-1 text-[13px]">
            {a.tiers.map(([k, v], i) => {
              const was = prior.hs[i]
              return (
                <li key={k} className="flex justify-between gap-3">
                  <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                  <span className="shrink-0 tnum">
                    {was && (
                      <span className="mr-2 text-[11px] line-through"
                        style={{ color: 'var(--text-muted)' }}>{usd(was[1])}</span>
                    )}
                    <span className="font-bold">{usd(v)}</span>
                  </span>
                </li>
              )
            })}
            <li className="flex justify-between gap-3 pt-1 border-t"
              style={{ borderColor: 'var(--grid)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Family cap</span>
              <span className="shrink-0 tnum">
                <span className="mr-2 text-[11px] line-through"
                  style={{ color: 'var(--text-muted)' }}>{usd(prior.hsCap)}</span>
                <span className="font-bold">{usd(a.familyCap)}</span>
              </span>
            </li>
          </ul>
          <ul className="text-[11px] mt-2 space-y-1" style={{ color: 'var(--text-muted)' }}>
            {a.notes.map(n => <li key={n.slice(0, 20)}>· {n}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>Bus transport, per year</p>
          <ul className="space-y-1 text-[13px]">
            {[['One student', 'full_single'], ['Two or more (family cap)', 'full_family'],
              ['One student, reduced', 'reduced_single'],
              ['Two or more, reduced', 'reduced_family']].map(([label, k]) => (
              <li key={k} className="flex justify-between gap-3">
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span className="font-bold tnum">{usd(f.bus[k] as number)}</span>
              </li>
            ))}
          </ul>
          <ul className="text-[11px] mt-2 space-y-1" style={{ color: 'var(--text-muted)' }}>
            {(f.bus.notes as string[]).map(n => <li key={n.slice(0, 20)}>· {n}</li>)}
          </ul>
        </div>
      </div>

      {!a.sourcePublished && (
        <div className="mt-4 p-3 rounded-lg text-[12px] leading-relaxed border"
          style={{ borderColor: 'var(--status-serious)', color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>
            The new schedule is not posted anywhere we can find.
          </strong>{' '}
          {a.sourceNote} The old figures are shown struck through above so you can see
          exactly what changed.
        </div>
      )}

      <p className="text-[12px] leading-relaxed mt-4 pt-3 border-t"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
        Blended across the sibling discount, athletics now works out around{' '}
        <strong>{usd(f.effectiveAthletic)} per participation</strong> — an estimated{' '}
        <strong>{usd(f.estimatedAthleticRevenue)} a year</strong>, or {pctOfProgram}% of
        the {usd(A.travel)} it costs to field the teams that survived and get them to away
        games. Under the old schedule that was {usd(f.priorEffectiveAthletic)} and about{' '}
        {priorPct}%, so the increase is worth roughly{' '}
        <strong>{usd(f.feeIncreaseValue)}</strong> a year if participation holds.
        The district publishes neither the schedule nor the collections, so these totals
        are our estimate — the arithmetic is on the{' '}
        <a href="#derivations" className="underline">Show the math</a> tab.
      </p>

      {a.unresolved.length > 0 && (
        <details className="mt-3">
          <summary className="text-[12px] font-semibold cursor-pointer"
            style={{ color: 'var(--text-secondary)' }}>
            What the announcement does not say ({a.unresolved.length})
          </summary>
          <ul className="text-[12px] mt-2 space-y-1.5 list-disc pl-4"
            style={{ color: 'var(--text-muted)' }}>
            {a.unresolved.map(n => <li key={n.slice(0, 20)}>{n}</li>)}
          </ul>
        </details>
      )}
    </div>
  )
}


/** Fee-to-cost coverage for one sport. Never colour alone — always a figure and a word. */
function Coverage({ pct }: { pct: number }) {
  const p = Math.max(0, pct)
  // Classify on the figure actually shown, so a rounded 100% never reads "Part-funded".
  const shown = Math.round(p * 100)
  const state = shown >= 100 ? 'full' : shown >= 50 ? 'part' : 'low'
  const color = state === 'full' ? 'var(--status-good)'
    : state === 'part' ? 'var(--status-serious)' : 'var(--status-critical)'
  const word = state === 'full' ? 'Pays its way'
    : state === 'part' ? 'Part-funded' : 'Subsidised'
  const glyph = state === 'full' ? '✓' : state === 'part' ? '◐' : '✕'
  return (
    <span className="flex items-center gap-2">
      <span className="h-2 rounded-full overflow-hidden shrink-0 w-14"
        style={{ background: 'var(--surface-3)' }}>
        <span className="block h-full rounded-full"
          style={{ width: `${Math.min(100, p * 100)}%`, background: color }} />
      </span>
      <span className="font-semibold tnum w-9 text-right">{shown}%</span>
      <span className="text-[10px] font-semibold whitespace-nowrap" style={{ color }}>
        <span aria-hidden="true">{glyph} </span>{word}
      </span>
    </span>
  )
}
