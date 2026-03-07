import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import {
  computeProp25,
  computeAnomalies,
  computeSchoolBreakdown,
  computeCostDriversChart,
  computeBudgetStory,
} from '../data/insights'
import { filterItemsForDepartment, DEPARTMENTS } from '../data/departments'
import { formatDollar, formatPct } from '../data/transforms'
import { CATEGORY_LABELS } from '../data/types'
import type { CategoryCode } from '../data/types'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'

// ── School color mappings ─────────────────────────────────────────────────────

const SCHOOL_COLORS: Record<string, string> = {
  ps: 'bg-sky-100 text-sky-800 border-sky-200',
  es: 'bg-amber-100 text-amber-800 border-amber-200',
  ms: 'bg-violet-100 text-violet-800 border-violet-200',
  hs: 'bg-rose-100 text-rose-800 border-rose-200',
}

const SCHOOL_BORDER: Record<string, string> = {
  ps: 'border-sky-300',
  es: 'border-amber-300',
  ms: 'border-violet-300',
  hs: 'border-rose-300',
}

// ── Program IDs for section 4 ─────────────────────────────────────────────────

const PROGRAM_IDS = ['sped', 'benefits', 'athletics', 'music', 'guidance', 'transportation', 'technology', 'facilities']

// ── Main page ─────────────────────────────────────────────────────────────────

export function HomePage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear, compareYear } = useBudgetStore()

  // Adjacent year for Prop 2½ (year immediately before primaryYear)
  const adjacentYear = useMemo(() => {
    if (!data) return compareYear
    const idx = data.years.findIndex(y => y.key === primaryYear)
    return idx > 0 ? data.years[idx - 1].key : data.years[0].key
  }, [data, primaryYear, compareYear])

  const prop25 = useMemo(
    () => (data ? computeProp25(data, primaryYear, adjacentYear) : null),
    [data, primaryYear, adjacentYear],
  )

  const budgetStory = useMemo(
    () => (data ? computeBudgetStory(data, primaryYear, adjacentYear) : null),
    [data, primaryYear, adjacentYear],
  )

  const anomalies = useMemo(
    () => (data ? computeAnomalies(data, primaryYear, compareYear) : []),
    [data, primaryYear, compareYear],
  )

  const schools = useMemo(
    () => (data ? computeSchoolBreakdown(data, primaryYear, compareYear).filter(s => s.id !== 'district') : []),
    [data, primaryYear, compareYear],
  )

  const topChanges = useMemo(
    () => (data ? computeCostDriversChart(data, primaryYear, compareYear, 10) : []),
    [data, primaryYear, compareYear],
  )

  // Program totals with top driver per program
  const programData = useMemo(() => {
    if (!data) return []
    return PROGRAM_IDS.map(id => {
      const dept = DEPARTMENTS.find(d => d.id === id)
      if (!dept) return null
      const items = filterItemsForDepartment(id, data, primaryYear, compareYear)
      const total = items.reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
      const totalCompare = items.reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
      const delta = total - totalCompare
      const pctChange = Math.abs(totalCompare) > 0.005 ? delta / totalCompare : null
      const topDriver = [...items]
        .filter(i => Math.abs(i.delta) > 500)
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0] ?? null
      return { id, label: dept.label, colorClass: dept.colorClass, total, delta, pctChange, topDriver }
    }).filter(Boolean) as Array<{
      id: string; label: string; colorClass: string
      total: number; delta: number; pctChange: number | null
      topDriver: { description: string; delta: number } | null
    }>
  }, [data, primaryYear, compareYear])

  // Cumulative growth (firstYear → primaryYear)
  const cumulativeGrowth = useMemo(() => {
    if (!data || data.years.length < 2) return null
    const firstKey = data.years[0].key
    const firstTotal = data.grandTotals[firstKey] ?? 0
    const currentTotal = data.grandTotals[primaryYear] ?? 0
    if (firstTotal < 0.005) return null
    return (currentTotal - firstTotal) / firstTotal
  }, [data, primaryYear])

  // Budget share leaders — which categories consume the most of the total
  const budgetShareLeaders = useMemo(() => {
    if (!data) return []
    const total = data.grandTotals[primaryYear] ?? 0
    if (total < 0.005) return []
    const catTotals = new Map<string, { label: string; amount: number }>()
    for (const g of data.groups) {
      if (!g.categoryCode || g.section === 'summary') continue
      const amt = g.totals[primaryYear] ?? 0
      if (!catTotals.has(g.categoryCode)) {
        catTotals.set(g.categoryCode, { label: CATEGORY_LABELS[g.categoryCode as CategoryCode] ?? g.categoryCode, amount: 0 })
      }
      catTotals.get(g.categoryCode)!.amount += amt
    }
    return [...catTotals.values()]
      .map(({ label, amount }) => ({ label, amount, pct: amount / total }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 3)
  }, [data, primaryYear])

  // Sustained growth / sustained cut: groups that moved in the same direction
  // across ALL of the last 3 non-projected year-over-year transitions
  const sustainedPatterns = useMemo(() => {
    if (!data) return { growth: null, cut: null }
    const nonProj = data.years.filter(y => !y.isProjected)
    if (nonProj.length < 3) return { growth: null, cut: null }
    // Need at least 3 years to get 2 transitions, prefer 4 years (3 transitions)
    const window = nonProj.slice(-(Math.min(nonProj.length, 4)))

    let bestGrowth: { label: string; transitions: number; totalDelta: number; code: string } | null = null
    let bestCut:    { label: string; transitions: number; totalDelta: number; code: string } | null = null

    for (const g of data.groups) {
      if (g.section === 'summary') continue
      const baseAmt = g.totals[window[0].key] ?? 0
      if (baseAmt < 25_000) continue // skip tiny groups — not interesting to public

      const changes: number[] = []
      for (let i = 1; i < window.length; i++) {
        const a = g.totals[window[i - 1].key] ?? 0
        const b = g.totals[window[i].key] ?? 0
        changes.push(b - a)
      }
      if (changes.length < 2) continue

      const allGrowing  = changes.every(c => c > 500)
      const allCutting  = changes.every(c => c < -500)
      const totalDelta  = changes.reduce((s, c) => s + c, 0)
      const cleanLabel  = g.label.replace(/^\d+\s*[-–]\s*/, '').trim()

      if (allGrowing && totalDelta > 20_000) {
        if (!bestGrowth || totalDelta > bestGrowth.totalDelta) {
          bestGrowth = { label: cleanLabel, transitions: changes.length, totalDelta, code: g.code }
        }
      }
      if (allCutting && Math.abs(totalDelta) > 10_000) {
        if (!bestCut || Math.abs(totalDelta) > Math.abs(bestCut.totalDelta)) {
          bestCut = { label: cleanLabel, transitions: changes.length, totalDelta, code: g.code }
        }
      }
    }

    return { growth: bestGrowth, cut: bestCut }
  }, [data])

  // Fastest-growing individual line item (high-severity spike)
  const fastestLineItem = useMemo(
    () => anomalies.find(a => a.type === 'spike' && a.severity === 'high') ?? anomalies.find(a => a.type === 'spike') ?? null,
    [anomalies],
  )

  const firstYearLabel = data?.years[0]?.short ?? ''
  const primaryLabel   = data?.years.find(y => y.key === primaryYear)?.label ?? primaryYear.toUpperCase()
  const compareLabel   = data?.years.find(y => y.key === compareYear)?.label ?? compareYear.toUpperCase()

  const grandTotal   = data?.grandTotals[primaryYear] ?? 0
  const grandCompare = data?.grandTotals[compareYear] ?? 0
  const grandDelta   = grandTotal - grandCompare
  const grandPct     = Math.abs(grandCompare) > 0.005 ? grandDelta / grandCompare : null

  const eliminatedCount    = anomalies.filter(a => a.type === 'eliminated').length
  const highSeverityCount  = anomalies.filter(a => a.severity === 'high').length

  const increases      = topChanges.filter(d => d.delta > 0).sort((a, b) => b.delta - a.delta)
  const cuts           = topChanges.filter(d => d.delta < 0).sort((a, b) => a.delta - b.delta)
  const biggestIncrease = increases[0] ?? null
  const biggestCut      = cuts[0] ?? null

  const totalLineItemCount = data?.lineItems.filter(i => !i.isGroupHeader && i.section !== 'summary').length ?? 0

  if (loading) return <div className="p-10 flex justify-center"><LoadingSpinner /></div>
  if (error || !data) return <ErrorBanner message={error ?? 'Could not load budget data.'} />

  // Budget story pull-quote: first ~220 chars of the opening paragraph
  const storyPullQuote = budgetStory?.paragraphs[0]
    ? budgetStory.paragraphs[0].slice(0, 220).replace(/\s\S*$/, '') + '…'
    : null

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-8">

      {/* ── Section 0: Override Alert Banner ─────────────────────────────────── */}
      {prop25 && prop25.isAboveCap ? (
        <div className="bg-red-50 border border-red-300 rounded-xl p-4 flex items-start gap-3">
          <span className="text-red-500 text-xl mt-0.5">⚠️</span>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-red-800 text-sm">Voter Action May Be Required</p>
            <p className="text-red-700 text-sm mt-1">
              The school district's {primaryLabel} budget request exceeds what Prop 2½ allows
              by <strong>{formatDollar(prop25.dollarAboveCap)}</strong>. Funding the full request
              would require a permanent override of the property tax levy — a vote at Town Meeting.
            </p>
            <Link to="/flow" className="inline-block mt-2 text-red-700 font-medium text-sm hover:underline">
              See how it's calculated →
            </Link>
          </div>
        </div>
      ) : prop25 ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 flex items-center gap-3">
          <span className="text-green-600 text-lg">✓</span>
          <p className="text-green-800 text-sm">
            The {primaryLabel} budget is within the Prop 2½ levy limit — no override needed.{' '}
            <Link to="/flow" className="font-medium hover:underline">See the calculation →</Link>
          </p>
        </div>
      ) : null}

      {/* ── Page header ───────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Lunenburg Public Schools Budget</h1>
        <p className="text-gray-500 text-sm mt-1">
          {primaryLabel} Proposed · compared to {compareLabel} · citizen analysis of public budget records
        </p>
      </div>

      {/* ── Section 1: Hook Stats ─────────────────────────────────────────────── */}
      <section>
        <h2 className="text-base font-bold text-gray-700 mb-3">What You Need to Know</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">

          {/* Total budget */}
          <Link to="/overview"
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
            <p className="text-xs text-gray-500 mb-1">Total Budget</p>
            <p className="text-xl font-bold text-gray-900">{formatDollar(grandTotal)}</p>
            <p className="text-xs text-gray-500 mt-1">
              {grandDelta >= 0 ? '+' : ''}{formatDollar(grandDelta)} from {compareLabel}
            </p>
            {grandPct !== null && <div className="mt-1"><DeltaBadge value={grandPct} size="sm" /></div>}
          </Link>

          {/* Cumulative growth */}
          <Link to="/yoy"
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
            <p className="text-xs text-gray-500 mb-1">Growth Since {firstYearLabel}</p>
            {cumulativeGrowth !== null ? (
              <>
                <p className="text-xl font-bold text-red-600">{formatPct(cumulativeGrowth)}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatDollar(data.grandTotals[data.years[0].key] ?? 0)} → {formatDollar(grandTotal)}
                </p>
              </>
            ) : (
              <p className="text-sm text-gray-400">Not enough data</p>
            )}
          </Link>

          {/* Programs eliminated */}
          <Link to="/insights"
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
            <p className="text-xs text-gray-500 mb-1">Programs Eliminated</p>
            {eliminatedCount > 0 ? (
              <>
                <p className="text-xl font-bold text-red-600">{eliminatedCount}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {eliminatedCount === 1 ? 'program or service' : 'programs or services'} cut entirely this year
                </p>
              </>
            ) : (
              <>
                <p className="text-xl font-bold text-green-600">None</p>
                <p className="text-xs text-gray-500 mt-1">Nothing was cut entirely this year</p>
              </>
            )}
          </Link>

          {/* Biggest named cut */}
          {biggestCut ? (
            <Link to={`/category/${encodeURIComponent(biggestCut.code)}`}
              className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
              <p className="text-xs text-gray-500 mb-1">Biggest Cut</p>
              <p className="text-sm font-semibold text-gray-800 leading-snug">{biggestCut.fullName}</p>
              <p className="text-xs text-green-700 font-medium mt-1">reduced by {formatDollar(Math.abs(biggestCut.delta))}</p>
              {biggestCut.pctChange !== null && <div className="mt-1"><DeltaBadge value={biggestCut.pctChange} size="sm" /></div>}
            </Link>
          ) : (
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">Biggest Cut</p>
              <p className="text-sm text-gray-400">No significant cuts this year</p>
            </div>
          )}

          {/* Biggest named investment */}
          {biggestIncrease && (
            <Link to={`/category/${encodeURIComponent(biggestIncrease.code)}`}
              className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
              <p className="text-xs text-gray-500 mb-1">Biggest Investment</p>
              <p className="text-sm font-semibold text-gray-800 leading-snug">{biggestIncrease.fullName}</p>
              <p className="text-xs text-red-600 font-medium mt-1">increased by {formatDollar(biggestIncrease.delta)}</p>
              {biggestIncrease.pctChange !== null && <div className="mt-1"><DeltaBadge value={biggestIncrease.pctChange} size="sm" /></div>}
            </Link>
          )}

          {/* High-severity anomalies */}
          <Link to="/insights"
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all">
            <p className="text-xs text-gray-500 mb-1">Unusual Changes Flagged</p>
            <p className="text-xl font-bold text-amber-600">{highSeverityCount}</p>
            <p className="text-xs text-gray-500 mt-1">high-severity line items with unusual year-over-year changes</p>
          </Link>

        </div>
      </section>

      {/* ── Budget Story Card ─────────────────────────────────────────────────── */}
      {storyPullQuote && (
        <section>
          <Link to="/insights"
            className="block bg-blue-50 border border-blue-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 bg-blue-600 rounded-lg p-2 flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h6M7 8h2" />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-blue-900">Read the Budget Story</p>
                <p className="text-xs text-blue-700 mt-1 leading-relaxed italic">
                  "{storyPullQuote}"
                </p>
                <p className="text-xs font-semibold text-blue-600 mt-2">
                  Read the full plain-English analysis →
                </p>
              </div>
            </div>
          </Link>
        </section>
      )}

      {/* ── Section 2: Prop 2½ Explainer Card ───────────────────────────────── */}
      {prop25 && (
        <section>
          <div className={`bg-white border-l-4 rounded-xl border border-gray-200 p-5 ${prop25.isAboveCap ? 'border-l-red-500' : 'border-l-green-500'}`}>
            <h2 className="font-bold text-gray-900 text-sm">Proposition 2½ — Property Tax Levy Limit</h2>
            <p className="text-sm text-gray-600 mt-2 max-w-2xl leading-relaxed">
              Massachusetts Prop 2½ limits how much the property tax levy can grow — 2.5% maximum per year.
              {prop25.isAboveCap
                ? ` The school district requested ${formatDollar(prop25.requestedTotal)}. The town's levy limit allows ${formatDollar(prop25.adjustedBase + prop25.capAmount)}. The gap of ${formatDollar(prop25.dollarAboveCap)} requires a voter-approved override at Town Meeting.`
                : ` The school's ${primaryLabel} request of ${formatDollar(prop25.requestedTotal)} falls within the Prop 2½ limit — no override is needed from school spending alone.`
              }
            </p>

            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">School Request</p>
                <p className="text-lg font-bold text-gray-900">{formatDollar(prop25.requestedTotal)}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Prop 2½ Ceiling</p>
                <p className="text-lg font-bold text-gray-900">{formatDollar(prop25.adjustedBase + prop25.capAmount)}</p>
              </div>
              <div className={`rounded-lg p-3 text-center ${prop25.isAboveCap ? 'bg-red-50' : 'bg-green-50'}`}>
                <p className="text-xs text-gray-500 mb-1">{prop25.isAboveCap ? 'Override Gap' : 'Under Cap By'}</p>
                <p className={`text-lg font-bold ${prop25.isAboveCap ? 'text-red-700' : 'text-green-700'}`}>
                  {formatDollar(Math.abs(prop25.dollarAboveCap))}
                </p>
              </div>
            </div>

            <div className="mt-3">
              <Link to="/flow" className="text-sm font-medium text-blue-600 hover:underline">
                See full step-by-step calculation →
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Section 3: Your Schools ──────────────────────────────────────────── */}
      {schools.length > 0 && (
        <section>
          <h2 className="text-base font-bold text-gray-700 mb-3">Your Schools</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {schools.map(school => {
              // Pick the most dramatic single movement within this school
              const topInc = school.increases[0] ?? null
              const topDec = school.decreases[0] ?? null
              const topMove = (topInc && topDec)
                ? (Math.abs(topInc.delta) >= Math.abs(topDec.delta) ? topInc : topDec)
                : (topInc ?? topDec)
              return (
                <Link key={school.id} to="/departments"
                  className={`bg-white border rounded-xl p-4 hover:shadow-sm transition-all flex flex-col ${SCHOOL_BORDER[school.id] ?? 'border-gray-200'}`}>
                  <span className={`inline-block self-start text-xs font-semibold px-2 py-0.5 rounded-full border mb-2 ${SCHOOL_COLORS[school.id] ?? 'bg-gray-100 text-gray-700 border-gray-200'}`}>
                    {school.abbrev}
                  </span>
                  <p className="text-sm font-semibold text-gray-800 leading-snug">{school.fullName}</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">{formatDollar(school.totalPrimary)}</p>
                  <div className="mt-1 flex items-center gap-1.5">
                    <DeltaBadge value={school.pctChange} size="sm" />
                    <span className="text-xs text-gray-400">vs {compareLabel}</span>
                  </div>
                  {topMove && (
                    <p className="text-xs text-gray-500 mt-2 leading-snug border-t border-gray-100 pt-2">
                      {topMove.delta > 0 ? '▲' : '▼'}{' '}
                      <span className="font-medium">{topMove.label}</span>
                      {' '}{topMove.delta > 0 ? '+' : ''}{formatDollar(topMove.delta)}
                    </p>
                  )}
                </Link>
              )
            })}
          </div>
        </section>
      )}

      {/* ── Section 4: Key Programs ───────────────────────────────────────────── */}
      {programData.length > 0 && (
        <section>
          <h2 className="text-base font-bold text-gray-700 mb-3">Key Programs</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {programData.map(prog => (
              <Link key={prog.id} to="/departments"
                className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all flex flex-col">
                <p className="text-xs font-medium text-gray-500 mb-1">{prog.label}</p>
                <p className="text-base font-bold text-gray-900">
                  {prog.total > 0 ? formatDollar(prog.total) : '—'}
                </p>
                {prog.total > 0 && (
                  <div className="mt-1 flex items-center gap-1.5">
                    <DeltaBadge value={prog.pctChange} size="sm" />
                    <span className="text-xs text-gray-400">vs {compareLabel}</span>
                  </div>
                )}
                {prog.topDriver && (
                  <p className="text-xs text-gray-500 mt-2 leading-snug border-t border-gray-100 pt-2">
                    {prog.topDriver.delta > 0 ? '▲' : '▼'}{' '}
                    <span className="font-medium">{prog.topDriver.description}</span>
                    {' '}{prog.topDriver.delta > 0 ? '+' : ''}{formatDollar(prog.topDriver.delta)}
                  </p>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ── Section 5: What Changed Most ─────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-gray-700">What Changed Most This Year</h2>
          <Link to="/yoy" className="text-xs text-blue-600 hover:underline">Full history →</Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-red-600 mb-3">▲ Largest Increases</h3>
            <div className="space-y-2">
              {increases.slice(0, 5).map(d => (
                <Link key={d.code} to={`/category/${encodeURIComponent(d.code)}`}
                  className="flex items-center justify-between hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 transition-colors">
                  <span className="text-sm text-gray-700 truncate mr-2">{d.fullName}</span>
                  <span className="text-sm font-semibold text-red-600 whitespace-nowrap">+{formatDollar(d.delta)}</span>
                </Link>
              ))}
              {increases.length === 0 && <p className="text-sm text-gray-400">No significant increases this year</p>}
            </div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-green-600 mb-3">▼ Largest Cuts</h3>
            <div className="space-y-2">
              {cuts.slice(0, 5).map(d => (
                <Link key={d.code} to={`/category/${encodeURIComponent(d.code)}`}
                  className="flex items-center justify-between hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 transition-colors">
                  <span className="text-sm text-gray-700 truncate mr-2">{d.fullName}</span>
                  <span className="text-sm font-semibold text-green-600 whitespace-nowrap">{formatDollar(d.delta)}</span>
                </Link>
              ))}
              {cuts.length === 0 && <p className="text-sm text-gray-400">No significant cuts this year</p>}
            </div>
          </div>
        </div>
      </section>

      {/* ── Patterns That Demand Attention ───────────────────────────────────── */}
      {(budgetShareLeaders.length > 0 || sustainedPatterns.growth || sustainedPatterns.cut || fastestLineItem) && (
        <section>
          <h2 className="text-base font-bold text-gray-700 mb-3">Patterns That Demand Attention</h2>
          <div className="space-y-3">

            {/* Budget share leader — biggest category by % of total */}
            {budgetShareLeaders[0] && (
              <Link to="/overview"
                className="block bg-white border-l-4 border-l-blue-400 border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-gray-900">
                      {budgetShareLeaders[0].label} consumes{' '}
                      <span className="text-blue-700">{(budgetShareLeaders[0].pct * 100).toFixed(0)}%</span> of the entire budget
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      At {formatDollar(budgetShareLeaders[0].amount)}, it's the single largest spending category —
                      {budgetShareLeaders[1] && ` followed by ${budgetShareLeaders[1].label} at ${(budgetShareLeaders[1].pct * 100).toFixed(0)}%.`}
                      {' '}Where does your tax dollar actually go?
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-blue-600 whitespace-nowrap mt-0.5">See breakdown →</span>
                </div>
              </Link>
            )}

            {/* Sustained growth pattern */}
            {sustainedPatterns.growth && (
              <Link to="/yoy"
                className="block bg-white border-l-4 border-l-red-400 border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-gray-900">
                      <span className="text-red-600">{sustainedPatterns.growth.label}</span> has grown
                      for {sustainedPatterns.growth.transitions} years in a row
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Not a one-time spike — an accumulated {formatDollar(sustainedPatterns.growth.totalDelta)} added
                      over {sustainedPatterns.growth.transitions + 1} years. Is the trend continuing?
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-blue-600 whitespace-nowrap mt-0.5">See history →</span>
                </div>
              </Link>
            )}

            {/* Sustained cut pattern */}
            {sustainedPatterns.cut && (
              <Link to="/yoy"
                className="block bg-white border-l-4 border-l-amber-400 border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-gray-900">
                      <span className="text-amber-700">{sustainedPatterns.cut.label}</span> has been cut
                      {sustainedPatterns.cut.transitions} years in a row
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      A total of {formatDollar(Math.abs(sustainedPatterns.cut.totalDelta))} removed over{' '}
                      {sustainedPatterns.cut.transitions + 1} years — a sustained reduction, not a single-year decision.
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-blue-600 whitespace-nowrap mt-0.5">See history →</span>
                </div>
              </Link>
            )}

            {/* Fastest-growing individual line item */}
            {fastestLineItem && (
              <Link to="/insights"
                className="block bg-white border-l-4 border-l-orange-400 border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-gray-900">
                      "<span className="text-orange-700">{fastestLineItem.description}</span>" jumped{' '}
                      {fastestLineItem.pctChange !== null ? formatPct(fastestLineItem.pctChange) : ''} in a single year
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      From {formatDollar(fastestLineItem.compareValue ?? 0)} to{' '}
                      {formatDollar(fastestLineItem.primaryValue ?? 0)} — one of the steepest single-year spikes
                      in the entire budget. See all flagged anomalies.
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-blue-600 whitespace-nowrap mt-0.5">See anomalies →</span>
                </div>
              </Link>
            )}

          </div>
        </section>
      )}

      {/* ── Explore Further ──────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-base font-bold text-gray-700 mb-3">Explore Further</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            {
              to: '/insights',
              label: 'Insights & Analysis',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>,
              hook: `${highSeverityCount} high-severity anomalies flagged — new items, eliminations, and unexplained spikes`,
            },
            {
              to: '/yoy',
              label: 'Year-Over-Year History',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>,
              hook: cumulativeGrowth !== null
                ? `Since ${firstYearLabel} the total budget has grown ${formatPct(cumulativeGrowth)} — see what drove every year`
                : 'See what drove budget changes across every year on record',
            },
            {
              to: '/flow',
              label: 'Prop 2½ & Override',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 13h.01M13 13h.01M9 10h.01M13 10h.01M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" /></svg>,
              hook: prop25?.isAboveCap
                ? `The school requested ${formatDollar(prop25.dollarAboveCap)} more than Prop 2½ allows — here's the math`
                : `The ${primaryLabel} budget is within the Prop 2½ levy limit — see the full calculation`,
            },
            {
              to: '/overview',
              label: 'Spending Breakdown',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>,
              hook: budgetShareLeaders[0]
                ? `${budgetShareLeaders[0].label} alone accounts for ${(budgetShareLeaders[0].pct * 100).toFixed(0)}% of all spending — see the full visual breakdown`
                : `Visual breakdown of all ${data.groups.filter(g => g.section !== 'summary').length} spending categories`,
            },
            {
              to: '/compare',
              label: 'Compare Years',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
              hook: `See how ${primaryLabel} and ${compareLabel} compare line by line`,
            },
            {
              to: '/departments',
              label: 'Schools & Departments',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>,
              hook: 'Explore all 4 schools and 10+ programs with line-item detail',
            },
            {
              to: '/search',
              label: 'Search',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
              hook: `Search across ${totalLineItemCount} individual budget line items`,
            },
            {
              to: '/guide',
              label: 'How to Read This',
              icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>,
              hook: 'New here? Learn what the budget numbers actually mean',
            },
          ].map(link => (
            <Link key={link.to} to={link.to}
              className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all flex items-start gap-3">
              <div className="mt-0.5 text-blue-500 flex-shrink-0">{link.icon}</div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900">{link.label}</p>
                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{link.hook}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

    </div>
  )
}
