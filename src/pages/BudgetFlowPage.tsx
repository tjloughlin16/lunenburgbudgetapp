import { useMemo } from 'react'
import { computeProp25 } from '../data/insights'
import { formatPct } from '../data/transforms'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { YearSelector } from '../components/filters/YearSelector'

const full$ = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

type Step = {
  color: string
  title: string
  headline: string
  formula: React.ReactNode
  badge?: React.ReactNode
  explanation: string
}

type SummaryRow = {
  label: string
  value: number
  color: string
  sublabel?: string
}

export function BudgetFlowPage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear } = useBudgetStore()

  // Derive the prior year as the year immediately before primaryYear in the years list.
  const priorYearKey = useMemo(() => {
    if (!data) return ''
    const idx = data.years.findIndex(y => y.key === primaryYear)
    return idx > 0 ? data.years[idx - 1].key : data.years[0].key
  }, [data, primaryYear])

  const m = useMemo(
    () => (data && priorYearKey ? computeProp25(data, primaryYear, priorYearKey) : null),
    [data, primaryYear, priorYearKey],
  )

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data || !m) return null

  const primaryLabel = data.years.find(y => y.key === primaryYear)?.label ?? primaryYear
  const compareLabel = data.years.find(y => y.key === priorYearKey)?.label ?? priorYearKey

  const hasTMData = m.townManagerTotal !== null
  const hasFreeCash = m.freeCashAdjust < 0

  const steps: Step[] = [
    // Step 1 — Prior Year Levy
    {
      color: 'bg-gray-400',
      title: 'Prior Year School Funding',
      headline: full$(m.adjustedBase),
      formula: hasFreeCash
        ? (
          <>
            {full$(m.totalCompare)} gross budget &minus; {full$(Math.abs(m.freeCashAdjust))} one-time free cash ={' '}
            <strong>{full$(m.adjustedBase)}</strong>
          </>
        )
        : <>{full$(m.totalCompare)} gross {compareLabel} total</>,
      explanation: `This is the amount Lunenburg taxpayers actually funded the schools at in ${compareLabel}. It's the starting point for everything below.`,
    },

    // Step 2 — Prop 2½ Cap
    {
      color: 'bg-blue-600',
      title: 'Prop 2½ Cap',
      headline: full$(m.adjustedBase + m.capAmount),
      formula: (
        <>
          {full$(m.adjustedBase)} &times; 2.5% = {full$(m.capAmount)} max increase &rarr; ceiling of{' '}
          <strong>{full$(m.adjustedBase + m.capAmount)}</strong>
        </>
      ),
      explanation:
        'Massachusetts Proposition 2½ limits how much the property tax levy can grow each year — maximum 2.5% without a voter-approved override.',
    },

    // Step 3 — Town Manager's Approved Budget (only if hasTMData)
    ...(hasTMData
      ? [
          {
            color: 'bg-emerald-600',
            title: "Town Manager's Approved Budget",
            headline: full$(m.totalPrimary),
            formula: (
              <>
                {full$(m.adjustedBase)} prior school funding + {full$(m.levyDelta)} approved increase ={' '}
                <strong>{full$(m.totalPrimary)}</strong> ({formatPct(m.levyPctChange)})
              </>
            ),
            badge:
              m.levyPctChange !== null ? (
                m.levyPctChange <= 0.025 ? (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                    Within 2.5% cap ({formatPct(m.levyPctChange)})
                  </span>
                ) : (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                    Slightly above 2.5% cap ({formatPct(m.levyPctChange)})
                  </span>
                )
              ) : undefined,
            explanation:
              `The Town Manager sets the official school budget allocation. This is the amount the schools operate on without a voter override.` +
              (m.levyPctChange !== null && m.levyPctChange > 0.025
                ? ' The overall town levy can accommodate this via new growth.'
                : ''),
          } satisfies Step,
        ]
      : []),

    // Step 4 — School's Proposed Budget
    {
      color: 'bg-amber-500',
      title: "School's Proposed Budget",
      headline: full$(m.requestedTotal),
      formula: (
        <>
          {full$(m.totalCompare)} last year + {full$(m.totalDelta)} requested increase ={' '}
          <strong>{full$(m.requestedTotal)}</strong> ({formatPct(m.budgetPctChange)})
        </>
      ),
      explanation: `The school district submitted its proposed budget — what it believes is needed. This is ${formatPct(m.budgetPctChange)} more than ${compareLabel}.`,
    },

    // Step 5 — Above cap / override (shown whenever the budget exceeded the 2.5% limit)
    ...(m.isAboveCap
      ? [
          {
            color: 'bg-red-600',
            title: hasTMData ? 'Override Needed' : 'Amount Above Prop 2½ Cap',
            headline: full$(hasTMData ? m.overrideAmount! : m.dollarAboveCap),
            badge: (() => {
              const pct = hasTMData ? m.budgetPctChange : m.levyPctChange
              const label = hasTMData ? 'school request vs +2.5% cap' : 'actual increase vs +2.5% cap'
              return pct !== null ? (
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-100 text-red-700">
                  {formatPct(pct)} {label}
                </span>
              ) : undefined
            })(),
            formula: hasTMData
              ? (
                <>
                  {full$(m.requestedTotal)} school request &minus; {full$(m.totalPrimary)} TM approved ={' '}
                  <strong>{full$(m.overrideAmount!)}</strong>
                </>
              )
              : (
                <>
                  {full$(m.levyDelta)} actual increase &minus; {full$(m.capAmount)} allowed (2.5%) ={' '}
                  <strong>{full$(m.dollarAboveCap)}</strong>
                </>
              ),
            explanation: hasTMData
              ? "This is the gap between the school's request and the Town Manager's allocation. Funding the full school budget requires voters to approve a Prop 2½ override at Town Meeting — a ballot vote that permanently raises the town's levy limit."
              : `The actual school budget increase of ${formatPct(m.levyPctChange)} exceeded the Prop 2½ cap of +2.5%. In prior years this gap was funded through a voter-approved override or accommodated via new growth in the town levy.`,
          } satisfies Step,
        ]
      : []),
  ]

  const summaryRows: SummaryRow[] = [
    { label: 'Prior Year School Funding', value: m.adjustedBase, color: 'text-gray-700' },
    { label: 'Prop 2½ Ceiling (base + 2.5%)', value: m.adjustedBase + m.capAmount, color: 'text-blue-700' },
    ...(hasTMData
      ? [{ label: "Town Manager's Approved Budget", value: m.totalPrimary, color: 'text-emerald-700' }]
      : []),
    { label: "School's Proposed Budget", value: m.requestedTotal, color: 'text-amber-700' },
    ...(m.isAboveCap
      ? [{
          label: hasTMData ? 'Override Gap' : 'Amount Above Cap',
          value: hasTMData ? m.overrideAmount! : m.dollarAboveCap,
          color: 'text-red-700',
          sublabel: (() => {
            const pct = hasTMData ? m.budgetPctChange : m.levyPctChange
            const label = hasTMData ? 'school request vs +2.5% cap' : 'actual increase vs +2.5% cap'
            return pct !== null ? `${formatPct(pct)} ${label}` : undefined
          })(),
        }]
      : []),
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">How It's Calculated</h1>
          <p className="text-gray-500 mt-0.5">
            Step-by-step walkthrough of how the {primaryLabel} school budget is set — from prior levy to override
          </p>
        </div>
        <YearSelector mode="primary" />
      </div>

      {/* Timeline */}
      <div className="max-w-2xl mx-auto">
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1
          return (
            <div key={step.title} className="flex gap-4">
              {/* Left: numbered circle + connecting line */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-9 h-9 rounded-full ${step.color} text-white flex items-center justify-center font-bold text-sm flex-shrink-0`}
                >
                  {i + 1}
                </div>
                {!isLast && <div className="w-0.5 bg-gray-200 flex-1 my-1" />}
              </div>

              {/* Right: card */}
              <div className="pb-8 flex-1">
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                    Step {i + 1}
                  </p>
                  <h2 className="text-base font-bold text-gray-900 mb-2">{step.title}</h2>
                  <p className="text-3xl font-bold tabular-nums text-gray-900">{step.headline}</p>

                  {/* Formula row */}
                  <div className="bg-gray-50 rounded-lg px-3 py-2 text-sm font-mono text-gray-700 mt-3">
                    {step.formula}
                  </div>

                  {/* Optional badge (e.g. cap status on Step 3) */}
                  {step.badge && <div className="mt-2">{step.badge}</div>}

                  <p className="text-sm text-gray-600 leading-relaxed mt-3">{step.explanation}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary callout */}
      <div className="max-w-2xl mx-auto bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
          <h2 className="text-sm font-bold text-gray-900">Quick Reference</h2>
          <p className="text-xs text-gray-500">All the key numbers at a glance</p>
        </div>
        <div className="divide-y divide-gray-100">
          {summaryRows.map((row, i) => (
            <div key={row.label} className="grid grid-cols-2 px-5 py-3">
              <span className="text-sm text-gray-600">
                {i + 1}. {row.label}
              </span>
              <div className="text-right">
                <span className={`text-sm font-bold tabular-nums ${row.color}`}>
                  {full$(row.value)}
                </span>
                {row.sublabel && (
                  <p className="text-xs text-gray-400 mt-0.5">{row.sublabel}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400 text-center max-w-2xl mx-auto pt-2">
        All figures computed from the published budget spreadsheet and supplemental Town Manager data. Change the year selector above to see how the calculation changes across fiscal years.
      </p>
    </div>
  )
}
