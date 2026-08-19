import { useEffect, useMemo, useState } from 'react'
import {
  MODEL, project, runCascade, usd, leverYield, leverStart, ladderTaken, ladderUnlawful,
  type Assumptions, type AppliedItem,
} from '../model/engine'
import {
  HS_SPORTS, participationsCut, programCost, scoreCuts, seedFromCuts, sportId, teamsCut,
  type CutState,
} from '../model/cuts'
import { Disclose, Note } from '../components/primitives'
import { ScenarioBar, type YearRemainder } from '../components/ScenarioBar'
import { LeverWorkbench } from '../components/Levers'
import { HealthInsurance } from '../components/HealthInsurance'
import { AthleticsFees } from '../components/Athletics'
import { GrowthCalculator } from '../components/TaxBase'
import { AssumptionsPanel } from '../components/Assumptions'
import { TeamSlider, TeamBoard } from '../components/SportCutter'
import { CutBoard } from '../components/CutBoard'
import { LadderDetail } from '../components/AdminLadder'

const startVals = () => Object.fromEntries(MODEL.levers.map(l => [l.id, leverStart(l)]))
const startBasis = () => Object.fromEntries(MODEL.levers.map(l => [l.id, l.basis]))

/** Every dial in one place.
 *
 *  This page owns its own scenario. It never reads from, and never writes to, the
 *  priorities page — a ranking can be loaded in as a starting point, but from that moment
 *  it is just a set of switches somebody chose, not a ranking any more. */
export function Adjust({ seed, onJump }: {
  /** A cut list handed over from the priorities page, with a nonce so the same list can
   *  be sent twice. */
  seed: { state: CutState; nonce: number } | null
  onJump: (anchor: string) => void
}) {
  const [a, setA] = useState<Assumptions>({ ...MODEL.assumptions })
  const [leverVals, setLeverVals] = useState<Record<string, number>>(startVals)
  const [leverBasis, setLeverBasis] = useState<Record<string, number>>(startBasis)
  const [movers, setMovers] = useState(0)
  const [migrationSaving, setMigrationSaving] = useState(0)
  const [newValue, setNewValue] = useState(MODEL.taxBase.currentNewGrowthValue)
  const [cuts, setCuts] = useState<CutState>({})
  const [loadedFrom, setLoadedFrom] = useState<string | null>(null)

  useEffect(() => {
    if (!seed) return
    setCuts(seed.state)
    setLoadedFrom('the ranking you set on the priorities page')
  }, [seed?.nonce])

  /* ---- the hole, before anything the reader has done ---- */
  const aGross = useMemo<Assumptions>(() => ({
    ...a, athletic_fee_revenue: 0,
    new_growth: MODEL.taxBase.currentNewGrowthRevenue,
  }), [a])
  const grossYears = useMemo(() => project(5, aGross), [aGross])
  const gap = grossYears[0].deficit

  /* ---- what the reader has done about it ---- */
  const cutScore = useMemo(() => scoreCuts(cuts), [cuts])
  const allTeamsCut = HS_SPORTS.every(s => (cuts[sportId(s)] ?? 0) > 0)

  // Cutting a team removes its athletes from the pool a fee can be charged on. Without
  // this the tool would cut Football and go on collecting Football's fees — the same
  // decision closing the gap twice, in opposite directions.
  const lostParticipations = participationsCut(cuts)
  const teamsGone = teamsCut(cuts).length
  const athleticPool = Math.max(0,
    (leverBasis.athletic_fees ?? MODEL.athletics.chargeableParticipations)
      - lostParticipations)
  // The fee's ceiling is what athletics costs, and that falls with the teams too.
  const costOf = (rungId: string) => programCost(rungId, cuts)
  const feePayers = {
    athletic_fees: {
      effective: athleticPool,
      removed: lostParticipations,
      reason: `participations on the ${teamsGone} team${teamsGone === 1 ? '' : 's'} you cut`,
      cap: costOf('travel'),
    },
  }
  const athleticCap = costOf('travel')

  const leverItems = useMemo<AppliedItem[]>(() => MODEL.levers.map(l => ({
    id: l.id,
    label: l.name,
    detail: l.isLadder
      ? ladderTaken(l, leverVals[l.id] ?? 0).map(r => r.label).join(' · ')
      : l.isPercent || l.isPercentPoint
        ? `${leverVals[l.id]}%${l.isPercentPoint ? ' employee share' : ' reduction'}`
        : `${usd(leverVals[l.id] ?? 0)} — ${l.unit}`,
    amount: Math.round(leverYield(
      l.id === 'athletic_fees' ? { ...l, cap: athleticCap } : l,
      leverVals[l.id] ?? 0,
      l.id === 'athletic_fees' ? athleticPool : leverBasis[l.id] ?? l.basis)),
    kind: 'lever' as const,
  })).filter(i => i.amount > 0), [leverVals, leverBasis, athleticPool, athleticCap])

  const newGrowthRevenue = (newValue * MODEL.taxBase.rate) / 1000
  const growthDelta = Math.round(newGrowthRevenue - MODEL.taxBase.currentNewGrowthRevenue)

  const found: AppliedItem[] = [
    ...leverItems,
    ...(migrationSaving > 0 ? [{
      id: 'health_migration', kind: 'lever' as const,
      label: 'Health insurance — plan migration',
      detail: `${movers} employees moved to a cheaper plan`,
      amount: Math.round(migrationSaving),
    }] : []),
    ...(growthDelta !== 0 ? [{
      id: 'new_growth', kind: 'lever' as const,
      label: growthDelta > 0 ? 'Extra commercial growth' : 'Less growth than assumed',
      detail: `${usd(newValue)} of new value a year, vs `
        + `${usd(MODEL.taxBase.currentNewGrowthValue)} assumed`,
      amount: growthDelta,
    }] : []),
  ]
  const cutItems: AppliedItem[] = cutScore.items
    .filter(i => i.amount > 0)
    .map(i => ({ id: i.id, label: i.label, detail: i.detail,
                 amount: Math.round(i.amount), kind: 'cut' as const }))
  const restoreItems: AppliedItem[] = cutScore.restores
    .map(i => ({ id: i.id, label: i.label, detail: i.detail,
                 amount: Math.round(i.amount), kind: 'cut' as const }))

  // Positions cut by a ladder lever are positions, and belong in the staffing figure
  // alongside the ones cut on the board below.
  const leverFte = MODEL.levers
    .filter(l => l.isLadder)
    .reduce((s, l) => s + ladderTaken(l, leverVals[l.id] ?? 0)
      .reduce((n, r) => n + r.fte, 0), 0)

  const foundTotal = found.reduce((s, i) => s + i.amount, 0)
  const cutTotal = cutItems.reduce((s, i) => s + i.amount, 0)
  const restoreTotal = cutScore.restoreTotal

  const years: YearRemainder[] = grossYears.map(y => ({
    fy: y.fy, gap: y.deficit,
    remaining: y.deficit + restoreTotal - foundTotal - cutTotal,
  }))

  /* ---- things that would otherwise be counted twice ---- */
  const warnings: string[] = []

  // Cutting something the Commonwealth requires is allowed here and counted honestly,
  // but it can never be allowed to look like an ordinary choice.
  const unlawfulLever = MODEL.levers
    .filter(l => l.isLadder)
    .flatMap(l => ladderUnlawful(l, leverVals[l.id] ?? 0))
  const unlawfulTotal = cutScore.unlawfulTotal
    + unlawfulLever.reduce((s, r) => s + r.amount, 0)
  const unlawfulCount = cutScore.unlawful.length + unlawfulLever.length
  if (unlawfulCount > 0)
    warnings.push(`${usd(unlawfulTotal)} of this comes from ${unlawfulCount} `
      + `${unlawfulCount === 1 ? 'thing' : 'things'} the Commonwealth requires the `
      + 'district to have. The arithmetic is real; the budget is not one that could be '
      + 'adopted. Look for the ⚖ marks.')
  const cutIn = (cat: string) =>
    cutScore.items.some(i => i.cat === cat && i.amount > 0)
  if ((leverVals.tech_cut ?? 0) > 0 && cutIn('technology'))
    warnings.push('The technology saving slider and the individual technology lines below '
      + 'come out of the same $638,675 budget — together they may double-count.')
  if (allTeamsCut && cutScore.restores.some(r => r.cat === 'athletics'))
    warnings.push('Every high school team is cut, but athletics pieces are being put back '
      + '— buses, coaches or trainers for teams that would no longer exist.')
  if (lostParticipations > 0
      && (leverVals.athletic_fees ?? 0) > MODEL.currentFees.effectiveAthletic)
    warnings.push(athleticPool <= 0
      ? 'Every team is cut, so the athletics fee raises nothing — there is no program '
        + 'left to charge for.'
      : `Cutting ${teamsGone} teams removed ${lostParticipations} of `
        + `${MODEL.athletics.chargeableParticipations} chargeable participations, so the `
        + `athletics fee is charged on ${athleticPool} athletes and raises less.`)

  /* ---- undo ---- */
  const resetItem = (id: string) => {
    if (id === 'new_growth') return setNewValue(MODEL.taxBase.currentNewGrowthValue)
    if (id === 'health_migration') { setMovers(0); return setMigrationSaving(0) }
    if (id.startsWith('restore:')) {
      const next = { ...cuts }
      delete next[id]
      return setCuts(next)
    }
    if (id.startsWith('sport:') || id.startsWith('ovh:')) {
      const next = { ...cuts }
      delete next[id]
      // Overhead is forced off while every team is cut, so undoing one has to put a
      // team back or the tick simply reappears.
      if (id.startsWith('ovh:') && allTeamsCut) {
        for (const sp of HS_SPORTS) delete next[sportId(sp)]
      }
      return setCuts(next)
    }
    const lever = MODEL.levers.find(l => l.id === id)
    if (lever) {
      setLeverVals({ ...leverVals, [id]: leverStart(lever) })
      setLeverBasis({ ...leverBasis, [id]: lever.basis })
      return
    }
    const next = { ...cuts }
    delete next[id]
    setCuts(next)
  }

  const resetAll = () => {
    setLeverVals(startVals()); setLeverBasis(startBasis())
    setA({ ...MODEL.assumptions })
    setMovers(0); setMigrationSaving(0)
    setNewValue(MODEL.taxBase.currentNewGrowthValue)
    setCuts({}); setLoadedFrom(null)
  }

  /** Seed the board from one of the published rankings, then let it be argued with. */
  const loadPreset = (key: string) => {
    const result = runCascade(MODEL.presets[key].order, aGross, 1)
    setCuts(seedFromCuts(result[0].cuts))
    setLoadedFrom(MODEL.presets[key].name)
  }

  const athFee = leverVals.athletic_fees ?? MODEL.currentFees.effectiveAthletic
  const empShare = (leverVals.health_design ?? 25) / 100

  return (
    <div>
      <ScenarioBar gap={gap} found={found} cuts={cutItems} restored={restoreItems}
        fte={cutScore.fte + leverFte - cutScore.restoreFte}
        years={years} warnings={warnings} onReset={resetAll} onResetItem={resetItem} />

      <div className="mx-auto max-w-6xl px-5 pt-8 pb-16 grid gap-8">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
            Close the {usd(gap)} yourself
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>
            Every dial that moves the FY28 gap is on this page. Raise money at the top, cut
            things at the bottom, and the bar above keeps the arithmetic. Nothing here
            touches the priorities page, and nothing is saved or sent anywhere.
          </p>
        </div>

        {/* ---------- start from a ranking ---------- */}
        <div className="card p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-1">
            <h2 className="text-[13px] font-bold">Start from somebody&rsquo;s priorities</h2>
            {loadedFrom && (
              <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                loaded from {loadedFrom}
              </span>
            )}
          </div>
          <p className="text-[12px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
            A blank page is a hard place to start. Load the FY28 cuts a published ranking
            produces, then argue with it item by item &mdash; put things back, take other
            things instead. Loading replaces whatever is currently cut and leaves the
            priorities page untouched.
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(MODEL.presets).map(([key, p]) => (
              <button key={key} onClick={() => loadPreset(key)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border"
                style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                {p.name}
              </button>
            ))}
            <button onClick={() => { setCuts({}); setLoadedFrom(null) }}
              disabled={Object.keys(cuts).length === 0}
              className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border disabled:opacity-30"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              Cut nothing
            </button>
          </div>
        </div>

        {/* ---------- raise money ---------- */}
        <div>
          <h2 className="text-lg font-bold mb-1">Fees, savings and cuts</h2>
          <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            Every dial that moves the gap on its own: fees and savings that raise money,
            and the two ladders that cut it &mdash; administration one position at a time,
            athletics one team at a time. Each has a catch, and the catch is under the
            dial. The argument behind the bigger ones is in the panels below them.{' '}
            <button onClick={() => onJump('the-money')} className="underline font-semibold"
              style={{ color: 'var(--series-cost)' }}>Why so little of this is possible →</button>
          </p>
          {/* The team dial rides directly after the athletics fee lever, because the two
              are one argument: charge more, or field fewer teams. Reading them a screen
              apart is how people conclude that a fee makes the choice go away. */}
          <LeverWorkbench gap={gap} vals={leverVals} setVals={setLeverVals}
            basis={leverBasis} setBasis={setLeverBasis} showTotal={false}
            zeroed={athleticPool <= 0 ? ['athletic_fees'] : []} payers={feePayers}
            after={{ athletic_fees: <TeamSlider state={cuts} setState={setCuts} /> }} />

          <div className="grid gap-3 mt-3">
            <Disclose title="Athletics fees, in detail"
              sub="What a fee raises against each version of the athletics program, and where raising it stops working.">
              <AthleticsFees fee={athFee} payers={athleticPool} teamsCut={teamsGone}
                costOf={costOf}
                setFee={n => setLeverVals({ ...leverVals, athletic_fees: n })} />
              <Note>
                This is the same control as the athletics fee slider above &mdash; move
                either one and both change.{' '}
                <button onClick={() => onJump('fees')} className="underline font-semibold"
                  style={{ color: 'var(--series-cost)' }}>
                  What families already pay →
                </button>
              </Note>
            </Disclose>

            <Disclose title="Athletics, team by team"
              sub="Every team with what it costs and how many play, the overhead that only moves when the last team goes, and what it would cost to put the middle school teams back.">
              <TeamBoard state={cuts} setState={setCuts} />
            </Disclose>

            <Disclose title="Administration, line by line"
              sub="Every position and budget line the slider walks through, what each one costs, and the point at which the ladder stops.">
              <LadderDetail id="admin_cut" value={leverVals.admin_cut ?? 0}
                setValue={n => setLeverVals({ ...leverVals, admin_cut: n })} />
            </Disclose>

            <Disclose title="Health insurance, in detail"
              sub="Who pays what today, and what a change to the split or the plan mix does to a family's pay packet.">
              <HealthInsurance empShare={empShare}
                setEmpShare={n => setLeverVals({ ...leverVals,
                  health_design: Math.round(n * 100) })}
                movers={movers} setMovers={setMovers} onSaving={setMigrationSaving} />
            </Disclose>

            <Disclose title="Commercial growth"
              sub="How much new commercial development the town adds each year, and what it is worth now and in ten years.">
              <GrowthCalculator gap={gap} newValue={newValue} setNewValue={setNewValue} />
              <Note>
                <button onClick={() => onJump('tax-base')} className="underline font-semibold"
                  style={{ color: 'var(--series-cost)' }}>
                  Why this takes a decade, and why houses make it worse →
                </button>
              </Note>
            </Disclose>
          </div>
        </div>

        {/* ---------- cuts ---------- */}
        <div>
          <h2 className="text-lg font-bold mb-1">Everything else you would stop paying for</h2>
          <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            One budget line at a time, for everything that is not athletics or
            administration. You can also go the other way &mdash; middle school sports,
            athletic transportation, the interventionists and the rest of the FY27 cut
            list can be <strong>put back</strong>, and each one adds to the gap rather
            than closing it. Amounts and staffing are the district&rsquo;s own published
            figures except where a line says otherwise.
          </p>
          <CutBoard state={cuts} setState={setCuts} onJump={onJump} />
        </div>

        {/* ---------- assumptions ---------- */}
        <Disclose title="The growth rates behind the gap"
          sub={`The ${usd(gap)} is not a fact — it is arithmetic on these rates, defaulted to what the district and town published for FY27. Change one and the gap moves.`}>
          <AssumptionsPanel a={a} setA={setA} leverTotal={foundTotal} />
        </Disclose>
      </div>
    </div>
  )
}
