import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useBudgetData } from '../hooks/useBudgetData'
import { formatDollar } from '../data/transforms'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import type { BudgetData } from '../data/types'

// ── Types ──────────────────────────────────────────────────────────────────────

type GroupChange = {
  code: string
  label: string
  categoryLabel: string | null
  section: string
  from: number
  to: number
  delta: number
  pctChange: number | null
}

type YearTransition = {
  fromShort: string
  toShort: string
  fromLabel: string
  toLabel: string
  totalFrom: number
  totalTo: number
  delta: number
  pctChange: number | null
  topIncreases: GroupChange[]
  topCuts: GroupChange[]
}

type PatternType = 'restoration' | 'recovery' | 'sustained-cut' | 'sustained-growth'

type MultiYearPattern = {
  code: string
  label: string
  categoryLabel: string | null
  section: string
  type: PatternType
  transitions: { fromShort: string; toShort: string; delta: number }[]
  firstYear: string
  firstValue: number
  latestValue: number
  netDelta: number
  netPct: number | null
  worstCutDelta: number
}

// ── Computation ────────────────────────────────────────────────────────────────

const MIN_SHOW     = 5_000   // min |delta| to show in a transition list
const MIN_PATTERN  = 15_000  // min |delta| for a transition to trigger pattern detection
const HEADLINE_MIN = 20_000  // min |netDelta| to appear as a headline callout

function computeTransitions(data: BudgetData): YearTransition[] {
  return data.years.slice(0, -1).map((fromYear, i) => {
    const toYear    = data.years[i + 1]
    const totalFrom = data.grandTotals[fromYear.key] ?? 0
    const totalTo   = data.grandTotals[toYear.key]   ?? 0
    const delta     = totalTo - totalFrom
    const pctChange = totalFrom > 0.005 ? delta / totalFrom : null

    const changes: GroupChange[] = data.groups
      .filter(g => g.lineItems.some(li => !li.isGroupHeader))
      .map(g => {
        const from = g.totals[fromYear.key] ?? 0
        const to   = g.totals[toYear.key]   ?? 0
        const d    = to - from
        return {
          code: g.code, label: g.label, categoryLabel: g.categoryLabel, section: g.section,
          from, to, delta: d,
          pctChange: from > 0.005 ? d / from : null,
        }
      })
      .filter(c => Math.abs(c.delta) >= MIN_SHOW)

    return {
      fromShort: fromYear.short, toShort: toYear.short,
      fromLabel: fromYear.label, toLabel: toYear.label,
      totalFrom, totalTo, delta, pctChange,
      topIncreases: changes.filter(c => c.delta > 0).sort((a, b) => b.delta - a.delta).slice(0, 5),
      topCuts:      changes.filter(c => c.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 5),
    }
  })
}

function computePatterns(data: BudgetData): MultiYearPattern[] {
  if (data.years.length < 3) return []

  const firstYear = data.years[0]
  const lastYear  = data.years[data.years.length - 1]

  return data.groups
    .filter(g => g.lineItems.some(li => !li.isGroupHeader))
    .flatMap(g => {
      const transitions = data.years.slice(0, -1).map((fy, i) => {
        const ty = data.years[i + 1]
        const from = g.totals[fy.key] ?? 0
        const to   = g.totals[ty.key] ?? 0
        return { fromShort: fy.short, toShort: ty.short, delta: to - from }
      })

      if (!transitions.some(t => Math.abs(t.delta) >= MIN_PATTERN)) return []

      const firstValue  = g.totals[firstYear.key]  ?? 0
      const latestValue = g.totals[lastYear.key]   ?? 0
      const netDelta    = latestValue - firstValue
      const netPct      = firstValue > 0.005 ? netDelta / firstValue : null

      const hasSigCut = transitions.some(t => t.delta < -MIN_PATTERN)
      const hasSigAdd = transitions.some(t => t.delta >  MIN_PATTERN)

      // Classify primarily on the actual net outcome (first year vs latest year).
      // This avoids the trap where several sub-threshold adds after a large cut
      // are missed by per-transition checks, causing a net-positive group to be
      // labelled "Sustained Cut" or a net-negative group to be missed as "Recovery".
      let type: PatternType
      if (netDelta >= 0) {
        if (hasSigCut) {
          type = 'restoration'      // had a cut at some point, now at or above baseline
        } else if (hasSigAdd) {
          type = 'sustained-growth' // meaningful adds, no significant cuts, net positive
        } else {
          return []
        }
      } else {
        // Net negative — below the first-year baseline
        if (hasSigAdd) {
          type = 'recovery'         // below baseline but at least one big year up
        } else {
          type = 'sustained-cut'    // below baseline, no meaningful individual recovery
        }
      }

      const worstCutDelta = Math.min(...transitions.map(t => t.delta))

      return [{
        code: g.code, label: g.label, categoryLabel: g.categoryLabel, section: g.section,
        type, transitions, firstYear: firstYear.short, firstValue, latestValue, netDelta, netPct,
        worstCutDelta,
      }] as MultiYearPattern[]
    })
    .sort((a, b) => Math.abs(b.netDelta) - Math.abs(a.netDelta))
}

type HeadlineKind = 'unrecovered-cut' | 'restoration' | 'recovery-gap' | 'growth-driver'

type Headline = {
  kind: HeadlineKind
  code: string
  label: string
  stat: number        // the big number shown prominently
  statLabel: string   // e.g. "below FY24 baseline"
  detail: string      // 1–2 sentence explanation
}

const RESTORATION_CUT_MIN = 40_000  // worst single-year cut must be at least this to be a notable restoration

function computeHeadlines(patterns: MultiYearPattern[]): Headline[] {
  const out: Headline[] = []

  // 1. Consistent growth drivers — largest first
  patterns
    .filter(p => p.type === 'sustained-growth' && p.netDelta >= HEADLINE_MIN)
    .sort((a, b) => b.netDelta - a.netDelta)
    .forEach(p => {
      out.push({
        kind: 'growth-driver',
        code: p.code, label: p.label,
        stat: p.netDelta,
        statLabel: `added since ${p.firstYear}`,
        detail: `Consistent budget growth every year — one of the larger drivers of cumulative spending increases.`,
      })
    })

  // 2. Unrecovered cuts — worst first
  patterns
    .filter(p => p.type === 'sustained-cut' && p.netDelta <= -HEADLINE_MIN)
    .sort((a, b) => a.netDelta - b.netDelta)
    .forEach(p => {
      const worst = p.transitions.reduce((w, t) => t.delta < w.delta ? t : w)
      out.push({
        kind: 'unrecovered-cut',
        code: p.code, label: p.label,
        stat: p.netDelta,
        statLabel: `vs ${p.firstYear} baseline`,
        detail: `Cut ${formatDollar(Math.abs(worst.delta))} in ${worst.toShort} with no significant recovery since.`,
      })
    })

  // 3. Restorations — only where the cut was large AND persisted at least one year
  // (i.e. the year immediately after the worst cut did not significantly bounce back)
  patterns
    .filter(p => {
      if (p.type !== 'restoration') return false
      if (p.worstCutDelta > -RESTORATION_CUT_MIN) return false
      const worstIdx = p.transitions.reduce(
        (wi, t, i) => t.delta < p.transitions[wi].delta ? i : wi, 0
      )
      const nextT = p.transitions[worstIdx + 1]
      // Exclude one-year blips: if the very next year added back >$10k it wasn't a lasting cut
      return !(nextT && nextT.delta > 10_000)
    })
    .sort((a, b) => a.worstCutDelta - b.worstCutDelta)
    .forEach(p => {
      const worst = p.transitions.reduce((w, t) => t.delta < w.delta ? t : w)
      const netStr = `${p.netDelta >= 0 ? '+' : ''}${formatDollar(p.netDelta)}`
      out.push({
        kind: 'restoration',
        code: p.code, label: p.label,
        stat: p.worstCutDelta,
        statLabel: `single-year cut in ${worst.toShort}`,
        detail: `Was cut then restored. Recent increases are recovery, not new spending. Net vs ${p.firstYear}: ${netStr}.`,
      })
    })

  // 4. Recovery gaps — largest gap first
  patterns
    .filter(p => p.type === 'recovery' && p.netDelta <= -HEADLINE_MIN)
    .sort((a, b) => a.netDelta - b.netDelta)
    .forEach(p => {
      out.push({
        kind: 'recovery-gap',
        code: p.code, label: p.label,
        stat: p.netDelta,
        statLabel: `still below ${p.firstYear} baseline`,
        detail: `Received some budget back but remains ${formatDollar(Math.abs(p.netDelta))} short of its ${p.firstYear} level.`,
      })
    })

  return out
}

// ── Sub-components ─────────────────────────────────────────────────────────────

const HEADLINE_STYLE: Record<HeadlineKind, {
  border: string; headerBg: string; badge: string; valueColor: string; title: string
}> = {
  'unrecovered-cut': {
    border: 'border-red-500', headerBg: 'bg-red-50',
    badge: 'bg-red-100 text-red-700', valueColor: 'text-red-700',
    title: 'Unrecovered Cut',
  },
  'restoration': {
    border: 'border-blue-400', headerBg: 'bg-blue-50',
    badge: 'bg-blue-100 text-blue-700', valueColor: 'text-blue-700',
    title: 'Restored After Cut',
  },
  'recovery-gap': {
    border: 'border-amber-400', headerBg: 'bg-amber-50',
    badge: 'bg-amber-100 text-amber-700', valueColor: 'text-amber-700',
    title: 'In Recovery',
  },
  'growth-driver': {
    border: 'border-gray-400', headerBg: 'bg-gray-50',
    badge: 'bg-gray-100 text-gray-700', valueColor: 'text-gray-700',
    title: 'Consistent Growth',
  },
}

function HeadlineCard({ h }: { h: Headline }) {
  const s = HEADLINE_STYLE[h.kind]
  const statStr = `${h.stat >= 0 ? '+' : ''}${formatDollar(h.stat)}`
  return (
    <Link to={`/category/${encodeURIComponent(h.code)}`} className="block h-full">
      <div className={`bg-white rounded-xl border-l-4 border border-gray-200 p-5 h-full hover:shadow-md transition-shadow cursor-pointer ${s.border}`}>
        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-bold mb-3 ${s.badge}`}>
          {h.kind === 'unrecovered-cut' && (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          )}
          {s.title}
        </div>
        <p className="text-sm font-bold text-gray-900 mb-4 leading-snug">{h.label}</p>
        <p className={`text-2xl font-bold tabular-nums ${s.valueColor}`}>{statStr}</p>
        <p className="text-xs text-gray-400 mt-0.5 mb-3">{h.statLabel}</p>
        <p className="text-xs text-gray-600 leading-relaxed">{h.detail}</p>
        <p className="text-xs text-blue-500 mt-3">View details →</p>
      </div>
    </Link>
  )
}

function ChangeRow({ item, dir }: { item: GroupChange; dir: 'add' | 'cut' }) {
  const isAdd = dir === 'add'
  const pctStr = item.pctChange !== null
    ? ` (${item.pctChange >= 0 ? '+' : ''}${(item.pctChange * 100).toFixed(1)}%)`
    : ''
  const row = (
    <div className="flex items-center gap-3 py-1.5 px-3 rounded hover:bg-gray-50 group">
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${isAdd ? 'bg-red-400' : 'bg-green-500'}`} />
      <span className="flex-1 text-sm text-gray-700 truncate group-hover:text-gray-900 leading-snug">
        {item.label}
        {item.categoryLabel && (
          <span className="ml-1.5 text-xs text-gray-400">{item.categoryLabel}</span>
        )}
      </span>
      <span className={`text-sm font-semibold tabular-nums whitespace-nowrap ${isAdd ? 'text-red-600' : 'text-green-600'}`}>
        {isAdd ? '+' : ''}{formatDollar(item.delta)}
        <span className="text-xs font-normal text-gray-400 ml-1">{pctStr}</span>
      </span>
    </div>
  )
  return item.code
    ? <Link to={`/category/${encodeURIComponent(item.code)}`}>{row}</Link>
    : row
}

function TransitionCard({ t }: { t: YearTransition }) {
  const isUp  = t.delta >= 0
  const pctStr = t.pctChange !== null
    ? ` (${t.pctChange >= 0 ? '+' : ''}${(t.pctChange * 100).toFixed(1)}%)`
    : ''

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Year banner */}
      <div className={`px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-3 ${isUp ? 'bg-red-50' : 'bg-green-50'}`}>
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-0.5">
            {t.fromShort} → {t.toShort}
          </p>
          <p className="text-sm text-gray-600">
            {t.fromLabel} to {t.toLabel}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-2xl font-bold tabular-nums ${isUp ? 'text-red-600' : 'text-green-600'}`}>
            {isUp ? '+' : ''}{formatDollar(t.delta)}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {formatDollar(t.totalFrom)} → {formatDollar(t.totalTo)}{pctStr}
          </p>
        </div>
      </div>

      {/* Two-column: adds / cuts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
        {/* Increases */}
        <div className="p-3">
          <p className="text-xs font-semibold text-red-500 uppercase tracking-wide px-3 mb-1">
            ▲ Largest Increases
          </p>
          {t.topIncreases.length === 0
            ? <p className="text-xs text-gray-400 px-3 py-2">No significant increases</p>
            : t.topIncreases.map(item => <ChangeRow key={item.code} item={item} dir="add" />)
          }
        </div>

        {/* Cuts */}
        <div className="p-3">
          <p className="text-xs font-semibold text-green-600 uppercase tracking-wide px-3 mb-1">
            ▼ Largest Cuts
          </p>
          {t.topCuts.length === 0
            ? <p className="text-xs text-gray-400 px-3 py-2">No significant cuts</p>
            : t.topCuts.map(item => <ChangeRow key={item.code} item={item} dir="cut" />)
          }
        </div>
      </div>
    </div>
  )
}

const PATTERN_CONFIG: Record<PatternType, {
  label: string
  description: string
  borderCls: string
  badgeCls: string
  headerBg: string
}> = {
  restoration: {
    label: 'Restored',
    description: 'Cut in a prior year, then brought back up — at or above the original level',
    borderCls: 'border-blue-400',
    badgeCls:  'bg-blue-100 text-blue-700',
    headerBg:  'bg-blue-50',
  },
  recovery: {
    label: 'Recovering',
    description: 'Cut in a prior year, partially added back — still below the original level',
    borderCls: 'border-amber-400',
    badgeCls:  'bg-amber-100 text-amber-700',
    headerBg:  'bg-amber-50',
  },
  'sustained-cut': {
    label: 'Sustained Cut',
    description: 'Budget reduced and has not come back',
    borderCls: 'border-orange-400',
    badgeCls:  'bg-orange-100 text-orange-700',
    headerBg:  'bg-orange-50',
  },
  'sustained-growth': {
    label: 'Consistent Growth',
    description: 'Budget has grown meaningfully each year',
    borderCls: 'border-gray-300',
    badgeCls:  'bg-gray-100 text-gray-600',
    headerBg:  'bg-gray-50',
  },
}

function PatternCard({ p }: { p: MultiYearPattern }) {
  const cfg    = PATTERN_CONFIG[p.type]
  const netUp  = p.netDelta >= 0
  const netPct = p.netPct !== null
    ? ` (${p.netPct >= 0 ? '+' : ''}${(p.netPct * 100).toFixed(1)}%)`
    : ''

  // Build a plain-English summary line
  const cutTransitions = p.transitions.filter(t => t.delta < -5000)
  const addTransitions = p.transitions.filter(t => t.delta >  5000)
  let summary = ''
  if (p.type === 'restoration' || p.type === 'recovery') {
    const cutDesc = cutTransitions.map(t => `${formatDollar(Math.abs(t.delta))} in ${t.toShort}`).join(', ')
    const addDesc = addTransitions.map(t => `+${formatDollar(t.delta)} in ${t.toShort}`).join(', ')
    summary = `Cut ${cutDesc}; then added ${addDesc}.`
  } else if (p.type === 'sustained-cut') {
    summary = `${formatDollar(Math.abs(p.netDelta))} below the ${p.firstYear} baseline with no significant recovery.`
  } else {
    summary = `Grown ${formatDollar(p.netDelta)} since ${p.firstYear}.`
  }

  return (
    <div className={`bg-white rounded-xl border-l-4 border border-gray-200 overflow-hidden ${cfg.borderCls}`}>
      <div className={`px-4 py-3 border-b border-gray-100 ${cfg.headerBg}`}>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className={`text-xs font-bold px-2 py-0.5 rounded whitespace-nowrap ${cfg.badgeCls}`}>
                {cfg.label}
              </span>
              {p.categoryLabel && (
                <span className="text-xs text-gray-400 truncate">{p.categoryLabel}</span>
              )}
            </div>
            <Link
              to={`/category/${encodeURIComponent(p.code)}`}
              className="text-sm font-bold text-gray-900 hover:text-blue-600 leading-snug block"
            >
              {p.label}
            </Link>
          </div>
          {/* Net change vs baseline */}
          <div className="text-right flex-shrink-0">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Net vs {p.firstYear}</p>
            <p className={`text-lg font-bold tabular-nums ${netUp ? 'text-red-600' : 'text-green-600'}`}>
              {netUp ? '+' : ''}{formatDollar(p.netDelta)}{netPct}
            </p>
          </div>
        </div>
      </div>

      {/* Summary line */}
      <div className="px-4 py-2 border-b border-gray-100 bg-white">
        <p className="text-xs text-gray-600 leading-relaxed">{summary}</p>
      </div>

      {/* Mini transition timeline */}
      <div className="px-4 py-3 flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-400 font-mono">{p.firstYear}</span>
        {p.transitions.map(t => {
          const isAdd = t.delta > 0
          const isCut = t.delta < 0
          const isFlat = !isAdd && !isCut
          return (
            <div key={t.toShort} className="flex items-center gap-2">
              <span className={`text-xs font-bold tabular-nums whitespace-nowrap ${
                isAdd ? 'text-red-500' : isCut ? 'text-green-600' : 'text-gray-300'
              }`}>
                {isFlat ? '→' : isAdd ? `+${formatDollar(t.delta)}` : `${formatDollar(t.delta)}`}
              </span>
              <span className="text-xs text-gray-400 font-mono">{t.toShort}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function YOYAnalysisPage() {
  const { data, loading, error } = useBudgetData()

  const transitions = useMemo(() => data ? computeTransitions(data) : [], [data])
  const patterns    = useMemo(() => data ? computePatterns(data)    : [], [data])
  const headlines   = useMemo(() => computeHeadlines(patterns),             [patterns])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBanner message={error} />
  if (!data)   return null

  const restorations   = patterns.filter(p => p.type === 'restoration')
  const recoveries     = patterns.filter(p => p.type === 'recovery')
  const sustainedCuts  = patterns.filter(p => p.type === 'sustained-cut')
  const growthItems    = patterns.filter(p => p.type === 'sustained-growth')

  const firstShort = data.years[0].short
  const lastShort  = data.years[data.years.length - 1].short

  return (
    <div className="p-6 space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Year-Over-Year History</h1>
        <p className="text-gray-500 mt-0.5">
          {firstShort} → {lastShort} — what changed each year, and how prior cuts shape today's budget
        </p>
      </div>

      {/* ── Annual transitions ─────────────────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-gray-900">Annual Changes</h2>
        {transitions.length === 0
          ? <p className="text-sm text-gray-400">Need at least two years of data.</p>
          : transitions.map(t => <TransitionCard key={`${t.fromShort}-${t.toShort}`} t={t} />)
        }
      </div>

      {/* ── Headlines ─────────────────────────────────────────────────────── */}
      {headlines.length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-gray-900">What Stands Out</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              The most significant multi-year budget stories — cuts, restorations, and growth drivers
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {headlines.map(h => <HeadlineCard key={h.code} h={h} />)}
          </div>
        </div>
      )}

      {/* ── Multi-year patterns ────────────────────────────────────────────── */}
      {patterns.length > 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-bold text-gray-900">The Cumulative Picture</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Budget lines with notable multi-year arcs — restorations, ongoing cuts, and consistent growth since {firstShort}
            </p>
          </div>

          {restorations.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold text-blue-700">Restored</p>
                <p className="text-xs text-gray-400">Cut in a prior year, brought back to or above baseline</p>
              </div>
              {restorations.map(p => <PatternCard key={p.code} p={p} />)}
            </div>
          )}

          {recoveries.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold text-amber-700">Recovering</p>
                <p className="text-xs text-gray-400">Was cut, partially added back — still below the original level</p>
              </div>
              {recoveries.map(p => <PatternCard key={p.code} p={p} />)}
            </div>
          )}

          {sustainedCuts.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold text-orange-700">Sustained Cuts</p>
                <p className="text-xs text-gray-400">Budget reduced and has not come back</p>
              </div>
              {sustainedCuts.map(p => <PatternCard key={p.code} p={p} />)}
            </div>
          )}

          {growthItems.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold text-gray-600">Consistent Growth</p>
                <p className="text-xs text-gray-400">Meaningful increases each year</p>
              </div>
              {growthItems.map(p => <PatternCard key={p.code} p={p} />)}
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-gray-400 text-center pt-2">
        Figures computed from published budget spreadsheets. Click any item to explore the full department.
      </p>
    </div>
  )
}
