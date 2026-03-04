import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { computeInsights, computeCostDriversChart, computeCategoryDriversChart, computeInsightSections, computeBudgetStory, computeSchoolBreakdown, computeAnomalies, computeProp25 } from '../data/insights'
import type { InsightCard, InsightType, InsightSection, InsightItem, CategoryDriversResult, SchoolBudget, Anomaly, AnomalyType, Prop25Metrics } from '../data/insights'
import { YearSelector } from '../components/filters/YearSelector'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { formatDollar, formatPct } from '../data/transforms'

// ── Budget story ─────────────────────────────────────────────────────────────

function BudgetStorySection({ story }: { story: ReturnType<typeof computeBudgetStory> }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-blue-50">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h6M7 8h2" />
          </svg>
          <h2 className="text-base font-bold text-blue-900">The Budget Story</h2>
        </div>
        <p className="text-xs text-blue-700 mt-1">
          A plain-English analysis of public budget documents — what the numbers mean for Lunenburg families
        </p>
      </div>

      <div className="px-6 py-5">
        {/* Pull-quote style leader line */}
        <div className="border-l-4 border-blue-300 pl-5 space-y-4">
          {story.paragraphs.map((para, i) => (
            <p key={i} className="text-gray-700 leading-relaxed text-sm">
              {para}
            </p>
          ))}
        </div>

        {/* Attribution */}
        <div className="mt-5 pt-4 border-t border-gray-100 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800">Lunenburg Budget Explorer</p>
            <p className="text-xs text-gray-400">{story.primaryLabel} · Citizen analysis of public budget records</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Card accent colors ────────────────────────────────────────────────────────

const BORDER: Record<InsightType, string> = {
  hero: 'border-blue-500', increase: 'border-red-400', decrease: 'border-green-500', neutral: 'border-gray-300',
}
const STAT_COLOR: Record<InsightType, string> = {
  hero: 'text-blue-700', increase: 'text-red-600', decrease: 'text-green-600', neutral: 'text-gray-600',
}
const ICON_BG: Record<InsightType, string> = {
  hero: 'bg-blue-100', increase: 'bg-red-50', decrease: 'bg-green-50', neutral: 'bg-gray-100',
}
const ICON_COLOR: Record<InsightType, string> = {
  hero: 'text-blue-600', increase: 'text-red-500', decrease: 'text-green-600', neutral: 'text-gray-400',
}

function CardIcon({ id, type }: { id: string; type: InsightType }) {
  const cls = `w-5 h-5 ${ICON_COLOR[type]}`
  if (id === 'hero') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
  if (id === 'top-increase') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
  if (id === 'cuts') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
  if (id === 'salaries') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
  if (id === 'classroom') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
  return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
}

function InsightCardView({ card, hero = false }: { card: InsightCard; hero?: boolean }) {
  const inner = (
    <div className={`bg-white rounded-xl border-l-4 border border-gray-200 p-5 flex flex-col gap-3 h-full ${BORDER[card.type]} ${card.href ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className={`p-2 rounded-lg ${ICON_BG[card.type]}`}>
          <CardIcon id={card.id} type={card.type} />
        </div>
        {card.href && <span className="text-xs text-blue-500 whitespace-nowrap mt-1">View details →</span>}
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">{card.title}</p>
        <p className={`font-bold ${hero ? 'text-3xl' : 'text-2xl'} ${STAT_COLOR[card.type]}`}>{card.stat}</p>
      </div>
      <p className={`text-gray-600 leading-relaxed ${hero ? 'text-base' : 'text-sm'}`}>{card.description}</p>
    </div>
  )
  return card.href ? <Link to={card.href} className="block h-full">{inner}</Link> : inner
}

// ── Cost drivers chart ────────────────────────────────────────────────────────

function CostDriversChart({ data }: { data: ReturnType<typeof computeCostDriversChart> }) {
  if (!data.length) return null

  const sorted = [...data].sort((a, b) => b.delta - a.delta)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-base font-bold text-gray-900">What's Driving the Change</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Dollar change per department — red bars increased, green bars decreased
        </p>
      </div>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={sorted.length * 36 + 40}>
          <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 80, left: 8, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
            <XAxis
              type="number"
              tickFormatter={v => formatDollar(v as number)}
              tick={{ fontSize: 10 }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="deptName"
              tick={{ fontSize: 11 }}
              width={172}
              tickLine={false}
              interval={0}
            />
            <Tooltip
              formatter={(value) => [
                `${(value as number) >= 0 ? '+' : ''}${formatDollar(value as number)}`,
                'Change',
              ]}
              labelFormatter={(label) => {
                const d = sorted.find(x => x.deptName === label)
                return d?.fullName ?? String(label)
              }}
            />
            <ReferenceLine x={0} stroke="#9ca3af" strokeWidth={1} />
            <Bar dataKey="delta" radius={[0, 3, 3, 0]}>
              {sorted.map((entry) => (
                <Cell
                  key={entry.code}
                  fill={entry.delta >= 0 ? '#f87171' : '#34d399'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Category drivers chart ────────────────────────────────────────────────────

function CategoryDriversChart({ result }: { result: CategoryDriversResult }) {
  const { rows, grossAdded, grossCut, net, addedDeptCount, cutDeptCount, expensesDelta, salariesDelta } = result
  if (!rows.length) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-base font-bold text-gray-900">Budget Adds &amp; Cuts by Category</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Net change per spending category — shows cuts that are hidden inside an overall increase
        </p>
      </div>

      {/* Summary banner: gross adds vs cuts, and expenses vs salaries */}
      <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-gray-100 border-b border-gray-100 text-center">
        <div className="px-4 py-3">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Added</p>
          <p className="text-base font-bold text-red-600 mt-0.5">+{formatDollar(grossAdded)}</p>
          <p className="text-xs text-gray-400">{addedDeptCount} dept{addedDeptCount !== 1 ? 's' : ''} up</p>
        </div>
        <div className="px-4 py-3">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Cut</p>
          <p className="text-base font-bold text-green-600 mt-0.5">{formatDollar(grossCut)}</p>
          <p className="text-xs text-gray-400">{cutDeptCount} dept{cutDeptCount !== 1 ? 's' : ''} down</p>
        </div>
        <div className="px-4 py-3 border-t sm:border-t-0">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Operating Expenses</p>
          <p className={`text-base font-bold mt-0.5 ${expensesDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {expensesDelta >= 0 ? '+' : ''}{formatDollar(expensesDelta)}
          </p>
          <p className="text-xs text-gray-400">non-salary</p>
        </div>
        <div className="px-4 py-3 border-t sm:border-t-0">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Salaries</p>
          <p className={`text-base font-bold mt-0.5 ${salariesDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {salariesDelta >= 0 ? '+' : ''}{formatDollar(salariesDelta)}
          </p>
          <p className="text-xs text-gray-400">compensation</p>
        </div>
      </div>

      {/* Net = the overall story in one line */}
      <div className="px-6 py-2 bg-gray-50 border-b border-gray-100 flex items-center gap-2 text-sm">
        <span className="text-gray-500">Net change:</span>
        <span className={`font-bold ${net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {net >= 0 ? '+' : ''}{formatDollar(net)}
        </span>
        <span className="text-gray-400 text-xs">= {formatDollar(grossAdded)} added − {formatDollar(Math.abs(grossCut))} cut</span>
      </div>

      {/* Bar chart */}
      <div className="p-4">
        <ResponsiveContainer width="100%" height={rows.length * 44 + 40}>
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 90, left: 8, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
            <XAxis
              type="number"
              tickFormatter={v => formatDollar(v as number)}
              tick={{ fontSize: 10 }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="catLabel"
              tick={{ fontSize: 11 }}
              width={140}
              tickLine={false}
              interval={0}
            />
            <Tooltip
              formatter={(value, key) => {
                const v = value as number
                const label = key === 'additions' ? 'Added' : key === 'reductions' ? 'Cut' : 'Net'
                return [`${v >= 0 ? '+' : ''}${formatDollar(v)}`, label]
              }}
              labelFormatter={(label) => String(label)}
            />
            <ReferenceLine x={0} stroke="#9ca3af" strokeWidth={1} />
            {/* Show stacked additions (red) and reductions (green) for the full picture */}
            <Bar dataKey="additions" stackId="split" fill="#f87171" radius={[0, 3, 3, 0]} />
            <Bar dataKey="reductions" stackId="split" fill="#34d399" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-400 mt-1 text-center">
          Red = added, Green = cut. Both bars shown per category — net position is where they balance.
        </p>
      </div>
    </div>
  )
}

// ── School breakdown ──────────────────────────────────────────────────────────

const SCHOOL_COLORS: Record<string, { bg: string; border: string; badge: string; text: string }> = {
  ps:       { bg: 'bg-sky-50',    border: 'border-sky-400',    badge: 'bg-sky-100 text-sky-700',    text: 'text-sky-700' },
  es:       { bg: 'bg-amber-50',  border: 'border-amber-400',  badge: 'bg-amber-100 text-amber-700', text: 'text-amber-700' },
  ms:       { bg: 'bg-violet-50', border: 'border-violet-400', badge: 'bg-violet-100 text-violet-700', text: 'text-violet-700' },
  hs:       { bg: 'bg-rose-50',   border: 'border-rose-400',   badge: 'bg-rose-100 text-rose-700',  text: 'text-rose-700' },
  district: { bg: 'bg-gray-50',   border: 'border-gray-300',   badge: 'bg-gray-100 text-gray-600',  text: 'text-gray-600' },
}

function SchoolCard({ school, compareLabel, primaryLabel }: {
  school: SchoolBudget
  compareLabel: string
  primaryLabel: string
}) {
  const colors = SCHOOL_COLORS[school.id] ?? SCHOOL_COLORS.district
  const isDistrict = school.id === 'district'

  return (
    <div className={`rounded-xl border-l-4 border border-gray-200 overflow-hidden ${colors.border}`}>
      {/* Header */}
      <div className={`px-4 py-3 ${colors.bg} border-b border-gray-100`}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${colors.badge}`}>
              {school.abbrev}
            </span>
            <h3 className="text-sm font-bold text-gray-900 mt-1">{school.fullName}</h3>
            {isDistrict && (
              <p className="text-xs text-gray-400 mt-0.5">Shared across all schools</p>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-base font-bold text-gray-900 tabular-nums">{formatDollar(school.totalPrimary)}</p>
            <p className={`text-sm font-semibold tabular-nums ${school.delta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {school.delta >= 0 ? '+' : ''}{formatDollar(school.delta)}
            </p>
            {school.pctChange !== null && (
              <p className={`text-xs tabular-nums ${school.delta >= 0 ? 'text-red-400' : 'text-green-500'}`}>
                {formatPct(school.pctChange)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Changes */}
      <div className="bg-white divide-y divide-gray-50">
        {school.increases.length === 0 && school.decreases.length === 0 && (
          <p className="px-4 py-3 text-xs text-gray-400">No significant changes from {compareLabel} to {primaryLabel}.</p>
        )}

        {school.increases.map(item => (
          <Link key={item.code} to={item.href} className="flex items-center gap-2 px-4 py-2 hover:bg-red-50 group">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
            <span className="flex-1 text-xs text-gray-700 group-hover:text-gray-900 leading-snug">{item.label}</span>
            <span className="text-xs font-semibold text-red-600 tabular-nums whitespace-nowrap">
              +{formatDollar(item.delta)}
            </span>
          </Link>
        ))}

        {school.decreases.map(item => (
          <Link key={item.code} to={item.href} className="flex items-center gap-2 px-4 py-2 hover:bg-green-50 group">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
            <span className="flex-1 text-xs text-gray-700 group-hover:text-gray-900 leading-snug">{item.label}</span>
            <span className="text-xs font-semibold text-green-600 tabular-nums whitespace-nowrap">
              {formatDollar(item.delta)}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function SchoolImpactSection({ schools, compareLabel, primaryLabel }: {
  schools: SchoolBudget[]
  compareLabel: string
  primaryLabel: string
}) {
  if (!schools.length) return null
  const buildingSchools = schools.filter(s => s.id !== 'district')
  const district = schools.find(s => s.id === 'district')

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h2 className="text-base font-bold text-gray-900">Impact by School</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {compareLabel} → {primaryLabel} — select your school to see what changed for your kids
          </p>
        </div>

        {/* Per-school cards */}
        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {buildingSchools.map(school => (
            <SchoolCard
              key={school.id}
              school={school}
              compareLabel={compareLabel}
              primaryLabel={primaryLabel}
            />
          ))}
        </div>

        {/* District-wide at bottom, full width */}
        {district && (
          <div className="px-4 pb-4">
            <SchoolCard school={district} compareLabel={compareLabel} primaryLabel={primaryLabel} />
          </div>
        )}
      </div>
    </div>
  )
}

// ── Detailed section ──────────────────────────────────────────────────────────

function SectionItemRow({ item }: { item: InsightItem }) {
  const isIncrease = item.delta > 0
  const isDecrease = item.delta < 0

  const row = (
    <div className={`flex items-start gap-3 py-2.5 px-4 border-b border-gray-50 last:border-0 ${item.href ? 'hover:bg-gray-50 cursor-pointer' : ''}`}>
      {/* Delta indicator */}
      <div className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${isIncrease ? 'bg-red-400' : isDecrease ? 'bg-green-500' : 'bg-gray-300'}`} />

      {/* Description + parent */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 leading-snug">{item.description}</p>
        {item.parentLabel && (
          <p className="text-xs text-gray-400 mt-0.5">
            {item.parentLabel}
            <span className={`ml-1.5 text-xs px-1 rounded ${item.section === 'salaries' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}`}>
              {item.section}
            </span>
          </p>
        )}
      </div>

      {/* Year values */}
      <div className="text-right flex-shrink-0 space-y-0.5">
        <div className={`text-sm font-semibold tabular-nums ${isIncrease ? 'text-red-600' : isDecrease ? 'text-green-600' : 'text-gray-500'}`}>
          {item.delta !== 0 ? `${isIncrease ? '+' : ''}${formatDollar(item.delta)}` : '—'}
        </div>
        {item.pctChange !== null && Math.abs(item.pctChange) > 0.005 && (
          <div className={`text-xs tabular-nums ${isIncrease ? 'text-red-400' : 'text-green-500'}`}>
            {formatPct(item.pctChange)}
          </div>
        )}
        {item.yearA !== null && item.yearB !== null && (
          <div className="text-xs text-gray-400 tabular-nums">
            {formatDollar(item.yearA)} → {formatDollar(item.yearB)}
          </div>
        )}
      </div>
    </div>
  )

  return item.href ? <Link to={item.href}>{row}</Link> : row
}

function DetailedSection({ section }: { section: InsightSection }) {
  const increases = section.items.filter(i => i.delta > 0)
  const decreases = section.items.filter(i => i.delta < 0)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-lg">{section.emoji}</span>
          <h2 className="text-base font-bold text-gray-900">{section.title}</h2>
          <span className="ml-auto text-xs text-gray-400">{section.items.length} line items</span>
        </div>
        <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">{section.intro}</p>
      </div>

      {section.items.length === 0 ? (
        <p className="px-6 py-4 text-sm text-gray-400">{section.noItemsText}</p>
      ) : (
        <div>
          {increases.length > 0 && (
            <div>
              <p className="px-4 py-2 text-xs font-semibold text-red-500 uppercase tracking-wide bg-red-50 border-b border-red-100">
                ▲ Increases ({increases.length})
              </p>
              {increases.map(item => <SectionItemRow key={item.id} item={item} />)}
            </div>
          )}
          {decreases.length > 0 && (
            <div>
              <p className="px-4 py-2 text-xs font-semibold text-green-600 uppercase tracking-wide bg-green-50 border-b border-green-100">
                ▼ Decreases ({decreases.length})
              </p>
              {decreases.map(item => <SectionItemRow key={item.id} item={item} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Prop 2½ banner ────────────────────────────────────────────────────────────

function Prop25Banner({ m, compareLabel }: { m: Prop25Metrics; compareLabel: string }) {
  if (m.levyPctChange === null && m.budgetPctChange === null) return null

  const isAbove    = m.isAboveCap
  const hasFreeCash = m.freeCashAdjust < 0
  const hasTMData  = m.townManagerTotal !== null
  const hasOverride = m.overrideAmount !== null && m.overrideAmount > 0

  const accentBorder = isAbove ? 'border-amber-300' : 'border-green-300'
  const accentBg     = isAbove ? 'bg-amber-50'      : 'bg-green-50'
  const accentText   = isAbove ? 'text-amber-900'   : 'text-green-900'
  const accentSub    = isAbove ? 'text-amber-700'   : 'text-green-700'
  const statColor    = isAbove ? 'text-amber-700'   : 'text-green-700'

  return (
    <div className={`rounded-xl border ${accentBorder} ${accentBg} overflow-hidden`}>
      {/* Header */}
      <div className={`px-6 py-3 border-b ${accentBorder} flex items-center gap-2`}>
        <svg className={`w-4 h-4 ${isAbove ? 'text-amber-600' : 'text-green-600'} flex-shrink-0`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {isAbove
            ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          }
        </svg>
        <h2 className={`text-sm font-bold ${accentText}`}>Proposition 2½ Context</h2>
        <span className={`ml-auto text-xs ${accentSub}`}>
          {isAbove
            ? (hasTMData ? "School request exceeds Town Manager's approved budget" : 'Levy increase exceeds the 2.5% annual cap')
            : (hasTMData ? "School request is within Town Manager's approved budget" : 'Levy increase is within the 2.5% annual cap')}
        </span>
      </div>

      {/* Override callout — most important number for residents */}
      {hasOverride && (
        <div className="px-6 py-4 bg-red-50 border-b border-red-200 flex items-start gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="text-sm font-bold text-red-800 mb-0.5">
              Potential Override: {formatDollar(m.overrideAmount!)}
            </p>
            <p className="text-xs text-red-700 leading-relaxed">
              The school's budget request ({formatDollar(m.requestedTotal)}) exceeds the Town Manager's approved allocation ({formatDollar(m.townManagerTotal!)}) by {formatDollar(m.overrideAmount!)}. Funding the full school request would require voters to approve a Prop 2½ override at Town Meeting.
            </p>
          </div>
        </div>
      )}

      {/* Free cash callout */}
      {hasFreeCash && (
        <div className="px-6 py-2 bg-white/70 border-b border-amber-100 flex items-start gap-2">
          <span className="text-amber-500 mt-0.5 flex-shrink-0">ⓘ</span>
          <p className="text-xs text-gray-600 leading-relaxed">
            <span className="font-semibold">{compareLabel} used {formatDollar(Math.abs(m.freeCashAdjust))} in one-time free cash</span>{' '}
            to offset that year's budget. Since that relief doesn't carry forward, the Prop 2½ cap is calculated from the actual levy base of {formatDollar(m.adjustedBase)}.
          </p>
        </div>
      )}

      {/* Metrics row */}
      <div className="grid grid-cols-3 divide-x divide-amber-100 bg-white/60">

        {/* School's requested budget */}
        <div className="px-4 py-4 text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">School Request</p>
          <p className="text-2xl font-bold tabular-nums text-gray-700">
            {formatDollar(m.requestedTotal)}
          </p>
          {m.budgetPctChange !== null && (
            <p className="text-xs text-gray-500 mt-1">
              {formatPct(m.budgetPctChange)} vs {compareLabel}
            </p>
          )}
        </div>

        {/* TM allowed / cap */}
        <div className="px-4 py-4 text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
            {hasTMData ? 'TM Allowed' : 'Prop 2½ Cap'}
          </p>
          <p className="text-2xl font-bold tabular-nums text-gray-500">
            {hasTMData ? formatDollar(m.totalPrimary) : '2.5%'}
          </p>
          <p className="text-xs text-gray-500 mt-1 tabular-nums">
            {hasTMData
              ? `+${formatDollar(m.levyDelta)} over prior levy`
              : `+${formatDollar(m.capAmount)} limit`}
          </p>
          {hasTMData && m.levyPctChange !== null && (
            <p className="text-xs text-gray-400 mt-0.5">{formatPct(m.levyPctChange)} increase</p>
          )}
        </div>

        {/* Override / above cap */}
        <div className="px-4 py-4 text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
            {isAbove ? (hasTMData ? 'Override Needed' : 'Above Cap') : 'Under Cap'}
          </p>
          <p className={`text-2xl font-bold tabular-nums ${statColor}`}>
            {formatDollar(Math.abs(m.dollarAboveCap))}
          </p>
          <p className={`text-xs mt-1 font-medium ${statColor}`}>
            {isAbove
              ? (hasTMData ? 'school above TM allowed' : 'above 2.5% threshold')
              : 'below threshold'}
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className={`px-6 py-3 border-t ${accentBorder}`}>
        <p className={`text-xs ${accentSub} leading-relaxed`}>
          <span className="font-semibold">Note:</span>{' '}
          Prop 2½ is measured against the entire town levy — not just schools — and state aid changes can offset some pressure. The levy analysis above reflects the Town Manager's allocation. The override amount reflects the gap between the school's full request and what the TM approved.
        </p>
      </div>
    </div>
  )
}

// ── Public review: anomalies ──────────────────────────────────────────────────

const ANOMALY_CONFIG: Record<AnomalyType, {
  label: string
  groupLabel: string
  badgeCls: string
  headerCls: string
}> = {
  'new':        { label: 'NEW',     groupLabel: 'New spending — line items that appeared this year',           badgeCls: 'bg-blue-100 text-blue-700',   headerCls: 'bg-blue-50 text-blue-700 border-blue-100' },
  'eliminated': { label: 'REMOVED', groupLabel: 'Removed — previously funded, now gone or near zero',         badgeCls: 'bg-orange-100 text-orange-700', headerCls: 'bg-orange-50 text-orange-700 border-orange-100' },
  'spike':      { label: 'SPIKE',   groupLabel: 'Unusual spikes — grew far faster than the overall budget',   badgeCls: 'bg-red-100 text-red-700',     headerCls: 'bg-red-50 text-red-700 border-red-100' },
  'sharp-cut':  { label: 'CUT',     groupLabel: 'Sharp cuts — fell well below prior-year funding levels',     badgeCls: 'bg-amber-100 text-amber-800', headerCls: 'bg-amber-50 text-amber-800 border-amber-100' },
}

function AnomalyRow({ anomaly }: { anomaly: Anomaly }) {
  const cfg = ANOMALY_CONFIG[anomaly.type]
  const { compareValue: va, primaryValue: vb, pctChange, type, section, severity } = anomaly

  const badgeLabel = (type === 'spike' || type === 'sharp-cut') && pctChange !== null
    ? formatPct(pctChange)
    : cfg.label

  return (
    <Link to={anomaly.href} className="block">
      <div className={`flex items-start gap-3 py-3 px-4 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors group ${severity === 'high' ? 'border-l-2 border-l-red-300' : ''}`}>
        {/* Type badge */}
        <div className="flex-shrink-0 pt-0.5 flex items-center gap-1">
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${cfg.badgeCls}`}>{badgeLabel}</span>
          {severity === 'high' && <span className="text-red-400 text-xs leading-none">●</span>}
        </div>

        {/* Description + parent */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 leading-snug truncate">{anomaly.description}</p>
          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
            <p className="text-xs text-gray-400 truncate">{anomaly.parentLabel}</p>
            <span className={`text-xs px-1 rounded ${section === 'salaries' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}`}>
              {section}
            </span>
          </div>
        </div>

        {/* Values: prev → current (hide the from→to line on mobile, always show delta) */}
        <div className="text-right flex-shrink-0 text-xs tabular-nums space-y-0.5">
          <div className="hidden sm:block text-gray-400">
            {va != null ? formatDollar(va) : <span className="italic">not budgeted</span>}
            {' → '}
            {vb != null ? (
              <span className={`font-semibold ${type === 'spike' || type === 'new' ? 'text-red-600' : 'text-green-700'}`}>
                {formatDollar(vb)}
              </span>
            ) : (
              <span className="font-semibold text-orange-600 italic">removed</span>
            )}
          </div>
          <div className={`font-semibold ${anomaly.delta >= 0 ? 'text-red-500' : 'text-green-600'}`}>
            {anomaly.delta >= 0 ? '+' : ''}{formatDollar(anomaly.delta)}
          </div>
        </div>

        <div className="flex-shrink-0 text-gray-300 group-hover:text-gray-400 self-center text-sm">→</div>
      </div>
    </Link>
  )
}

function PublicReviewSection({ anomalies, primaryLabel, compareLabel }: {
  anomalies: Anomaly[]
  primaryLabel: string
  compareLabel: string
}) {
  if (!anomalies.length) return null

  const byType = (t: AnomalyType) => anomalies.filter(a => a.type === t)
  const groups: { type: AnomalyType; items: Anomaly[] }[] = (
    [
      { type: 'new'        as AnomalyType, items: byType('new') },
      { type: 'eliminated' as AnomalyType, items: byType('eliminated') },
      { type: 'spike'      as AnomalyType, items: byType('spike') },
      { type: 'sharp-cut'  as AnomalyType, items: byType('sharp-cut') },
    ] as { type: AnomalyType; items: Anomaly[] }[]
  ).filter(g => g.items.length > 0)

  const highCount = anomalies.filter(a => a.severity === 'high').length

  return (
    <div className="bg-white rounded-xl border border-amber-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-6 py-4 border-b border-amber-100 bg-amber-50">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-amber-900">Worth a Closer Look</h2>
            <p className="text-xs text-amber-700 mt-0.5">
              {anomalies.length} line item{anomalies.length !== 1 ? 's' : ''} from {compareLabel} → {primaryLabel} outside normal year-over-year patterns.
              {highCount > 0 && <span className="font-semibold"> {highCount} high-significance (● marker).</span>}
            </p>
            {/* Summary chips — below description so they don't crowd mobile */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              {byType('new').length > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 bg-blue-100 text-blue-700 rounded">{byType('new').length} new</span>
              )}
              {byType('eliminated').length > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 bg-orange-100 text-orange-700 rounded">{byType('eliminated').length} removed</span>
              )}
              {byType('spike').length > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 bg-red-100 text-red-700 rounded">{byType('spike').length} spike{byType('spike').length !== 1 ? 's' : ''}</span>
              )}
              {byType('sharp-cut').length > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 bg-amber-100 text-amber-800 rounded">{byType('sharp-cut').length} sharp cut{byType('sharp-cut').length !== 1 ? 's' : ''}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Grouped rows */}
      {groups.map(({ type, items }) => {
        const cfg = ANOMALY_CONFIG[type]
        return (
          <div key={type}>
            <p className={`px-4 py-2 text-xs font-semibold uppercase tracking-wide border-b ${cfg.headerCls}`}>
              {cfg.groupLabel} ({items.length})
            </p>
            {items.map(a => <AnomalyRow key={a.id} anomaly={a} />)}
          </div>
        )
      })}

      {/* Footer note */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Methodology: "new" = not budgeted in prior year; "removed" = was funded, now gone; "spike" = grew &gt;50% with &gt;$15k added; "sharp cut" = fell &gt;40% with &gt;$10k removed.
          High-significance (●) = &gt;$50–60k impact. Click any row to explore the full budget group.
        </p>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function InsightsPage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear } = useBudgetStore()

  // Always compare against the year immediately before primaryYear.
  // The global compareYear store value is not used here because the page
  // only shows a primary year selector — leaving compareYear stuck at the
  // default would produce backwards comparisons when browsing prior years.
  const priorYearKey = useMemo(() => {
    if (!data) return ''
    const idx = data.years.findIndex(y => y.key === primaryYear)
    return idx > 0 ? data.years[idx - 1].key : data.years[0].key
  }, [data, primaryYear])

  const cards = useMemo(
    () => (data ? computeInsights(data, primaryYear, priorYearKey) : []),
    [data, primaryYear, priorYearKey]
  )

  const chartData = useMemo(
    () => (data ? computeCostDriversChart(data, primaryYear, priorYearKey) : []),
    [data, primaryYear, priorYearKey]
  )

  const categoryDrivers = useMemo(
    () => (data ? computeCategoryDriversChart(data, primaryYear, priorYearKey) : null),
    [data, primaryYear, priorYearKey]
  )

  const sections = useMemo(
    () => (data ? computeInsightSections(data, primaryYear, priorYearKey) : []),
    [data, primaryYear, priorYearKey]
  )

  const schools = useMemo(
    () => (data ? computeSchoolBreakdown(data, primaryYear, priorYearKey) : []),
    [data, primaryYear, priorYearKey]
  )

  const story = useMemo(
    () => (data ? computeBudgetStory(data, primaryYear, priorYearKey) : null),
    [data, primaryYear, priorYearKey]
  )

  const anomalies = useMemo(
    () => (data ? computeAnomalies(data, primaryYear, priorYearKey) : []),
    [data, primaryYear, priorYearKey]
  )

  const prop25 = useMemo(
    () => (data ? computeProp25(data, primaryYear, priorYearKey) : null),
    [data, primaryYear, priorYearKey]
  )

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const hero = cards.find(c => c.id === 'hero')
  const rest = cards.filter(c => c.id !== 'hero')
  const primaryLabel = data.years.find(y => y.key === primaryYear)?.label ?? primaryYear
  const compareLabel = data.years.find(y => y.key === priorYearKey)?.label ?? priorYearKey

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Budget Insights</h1>
          <p className="text-gray-500 mt-0.5">
            {primaryLabel} — plain-English analysis for the general public
          </p>
        </div>
        <YearSelector mode="primary" />
      </div>

      {/* Prop 2½ banner */}
      {prop25 && <Prop25Banner m={prop25} compareLabel={compareLabel} />}

      {/* Story */}
      {story && <BudgetStorySection story={story} />}

      {/* Hero */}
      {hero && <InsightCardView card={hero} hero />}

      {/* Cost drivers chart + category adds/cuts */}
      <CostDriversChart data={chartData} />
      {categoryDrivers && <CategoryDriversChart result={categoryDrivers} />}

      {/* Summary cards grid */}
      {rest.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rest.map(card => <InsightCardView key={card.id} card={card} />)}
        </div>
      )}

      {/* Public review: anomalies */}
      <PublicReviewSection
        anomalies={anomalies}
        primaryLabel={primaryLabel}
        compareLabel={compareLabel}
      />

      {/* School impact */}
      {schools.length > 0 && (
        <SchoolImpactSection
          schools={schools}
          compareLabel={compareLabel}
          primaryLabel={primaryLabel}
        />
      )}

      {/* Divider */}
      {sections.length > 0 && (
        <div className="flex items-center gap-4 pt-2">
          <div className="flex-1 h-px bg-gray-200" />
          <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Deeper Dive</p>
          <div className="flex-1 h-px bg-gray-200" />
        </div>
      )}

      {/* Detailed thematic sections */}
      {sections.map(section => (
        <DetailedSection key={section.id} section={section} />
      ))}

      <p className="text-xs text-gray-400 text-center pt-2">
        Figures computed from the published budget spreadsheet. Click any row to explore the underlying department.
      </p>
    </div>
  )
}
