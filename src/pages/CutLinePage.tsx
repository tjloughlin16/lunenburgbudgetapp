import { useState, useMemo } from 'react'
import { useBudgetData } from '../hooks/useBudgetData'
import { useBudgetStore } from '../store/budgetStore'
import { computeProp25 } from '../data/insights'

// ── Types ─────────────────────────────────────────────────────────────────────

type Tier = 1 | 2 | 3
type CutFlag = 'negotiation' | 'legal' | 'warning'

interface CutOption {
  id: string
  tier: Tier
  category: string
  label: string
  detail: string
  savingsMin: number
  savingsMax: number
  priority: number        // determines auto-selection order (lower = cut first)
  notes?: string
  flag?: CutFlag
  classSizeTarget?: number  // set on class size rows; drives the class size indicator
}

// ── Class size helpers ────────────────────────────────────────────────────────

const ENROLLMENT      = 1_750
const TEACHER_COST    = 95_000
const BASE_CLASS_SIZE = 22

// Incremental savings going from one class size step to the next
function incrementalSavings(from: number, to: number): { min: number; max: number } {
  const sectionsFrom = Math.ceil(ENROLLMENT / from)
  const sectionsTo   = Math.ceil(ENROLLMENT / to)
  const eliminated   = Math.max(0, sectionsFrom - sectionsTo)
  const mid          = eliminated * TEACHER_COST
  return { min: Math.round(mid * 0.9), max: Math.round(mid * 1.1) }
}

const CS_24 = incrementalSavings(22, 24)  // 22 → 24
const CS_25 = incrementalSavings(24, 25)  // 24 → 25
const CS_27 = incrementalSavings(25, 27)  // 25 → 27
const CS_28 = incrementalSavings(27, 28)  // 27 → 28
const CS_30 = incrementalSavings(28, 30)  // 28 → 30
const CS_33 = incrementalSavings(30, 33)  // 30 → 33

// ── Cut data ─────────────────────────────────────────────────────────────────
// Ordered by priority (lower number = cut earlier / less painful)
// Class size rows are woven in at realistic deficit thresholds

const CUT_OPTIONS: CutOption[] = [

  // ── TIER 1: Low Impact ────────────────────────────────────────────────────
  {
    id: 'freeze-positions',
    tier: 1, priority: 10,
    category: 'Staffing',
    label: 'Freeze 2–3 open teaching positions',
    detail: 'When teachers retire or resign, leave positions unfilled or cover by combining sections.',
    savingsMin: 170_000, savingsMax: 315_000,
    notes: 'Attrition-based — no layoffs. Nearly invisible to most families.',
  },
  {
    id: 'freeze-discretionary',
    tier: 1, priority: 15,
    category: 'Operations',
    label: 'Freeze supplies & discretionary spending',
    detail: 'No new textbooks, postpone technology refresh cycles, reduce supply and field trip budgets.',
    savingsMin: 50_000, savingsMax: 150_000,
  },
  {
    id: 'reduce-pd',
    tier: 1, priority: 18,
    category: 'Operations',
    label: 'Freeze professional development & conference travel',
    detail: 'Cancel off-site conference travel and external PD vendor contracts. High symbolic value; low harm.',
    savingsMin: 20_000, savingsMax: 50_000,
  },
  {
    id: 'cut-saas',
    tier: 1, priority: 20,
    category: 'Operations',
    label: 'Cut vendor & SaaS software subscriptions',
    detail: 'Cancel curriculum platforms, assessment tools, and admin software not under locked contracts.',
    savingsMin: 30_000, savingsMax: 80_000,
  },
  {
    id: 'cut-stipends',
    tier: 1, priority: 25,
    category: 'Programs',
    label: 'Cut 15–20 club & activity stipends',
    detail: 'Eliminate lower-enrollment clubs. Advisor stipends run $1,500–$4,000 each.',
    savingsMin: 30_000, savingsMax: 60_000,
    notes: 'Low visibility to families. More visible to staff.',
  },
  {
    id: 'cut-admin-asst',
    tier: 1, priority: 28,
    category: 'Administration',
    label: 'Reduce administrative assistant positions',
    detail: 'Cut office support hours or eliminate a front-office position at a smaller school.',
    savingsMin: 45_000, savingsMax: 90_000,
  },
  {
    id: 'instrument-fees',
    tier: 1, priority: 30,
    category: 'Programs',
    label: 'Charge instrument rental fees (band & orchestra)',
    detail: 'Shift cost of school-owned instrument maintenance and rentals to families ($50–$150/yr).',
    savingsMin: 15_000, savingsMax: 40_000,
    notes: 'May reduce participation among lower-income families.',
  },
  {
    id: 'cut-enrichment',
    tier: 1, priority: 33,
    category: 'Programs',
    label: 'Cut after-school enrichment programs',
    detail: 'Eliminate paid after-school tutoring and extended learning funded through the operating budget.',
    savingsMin: 50_000, savingsMax: 150_000,
  },
  {
    id: 'late-bus',
    tier: 1, priority: 36,
    category: 'Transportation',
    label: 'Eliminate late bus routes',
    detail: 'Cancel after-school activity buses. Students must arrange their own ride home from sports and clubs.',
    savingsMin: 25_000, savingsMax: 60_000,
    flag: 'warning',
    notes: 'Limits extracurriculars to students with a ride — inequitable across income levels.',
  },

  // ── TIER 2: Visible Cuts ──────────────────────────────────────────────────
  {
    id: 'pay-to-play',
    tier: 2, priority: 40,
    category: 'Athletics',
    label: 'Raise athletic fees further',
    detail: 'Lunenburg already charges — $400 first child, $300 second, $225 third, $1,500 family cap for 2026-27, up from $250/$140/$85. Only a further increase is new money.',
    savingsMin: 40_000, savingsMax: 110_000,
    flag: 'warning',
    notes: 'Most of the headroom is already spent. Revenue peaks near $1,185 a season; past that, participation falls faster than the fee rises.',
  },
  {
    id: 'cut-ms-sports',
    tier: 2, priority: 43,
    category: 'Athletics',
    label: 'Cut middle school athletics entirely',
    detail: 'Eliminate all MS sports — coach stipends, transportation, equipment. No MIAA championship implications.',
    savingsMin: 80_000, savingsMax: 150_000,
    notes: 'Most common first full athletics cut in Massachusetts suburban districts.',
  },
  {
    id: 'cut-librarian',
    tier: 2, priority: 46,
    category: 'Staffing',
    label: 'Cut or share librarian position',
    detail: 'Reduce certified librarian to part-time, or one librarian serves two buildings on alternating days.',
    savingsMin: 40_000, savingsMax: 60_000,
  },
  {
    id: 'cut-coordinator',
    tier: 2, priority: 49,
    category: 'Administration',
    label: 'Eliminate a district coordinator role',
    detail: 'Remove a curriculum, STEM, or ELL coordinator position.',
    savingsMin: 90_000, savingsMax: 120_000,
  },
  {
    id: 'cut-drama',
    tier: 2, priority: 52,
    category: 'Programs',
    label: 'Cut performing arts & drama productions',
    detail: 'Eliminate school musical and drama productions. Cut related staffing and materials budgets.',
    savingsMin: 30_000, savingsMax: 70_000,
  },
  {
    id: 'cut-specialist',
    tier: 2, priority: 55,
    category: 'Staffing',
    label: 'Cut 1 specialist teacher (art / music / PE)',
    detail: 'Reduce specials from 5 days/week to 4 and share a teacher across buildings, eliminating one FTE.',
    savingsMin: 85_000, savingsMax: 105_000,
  },
  // First class size step — Tier 2, just above contract norms
  {
    id: 'classsize-24',
    tier: 2, priority: 57,
    category: 'Class Size',
    label: 'Increase class size: 22 → 24 students',
    detail: `Eliminates ~${Math.ceil(ENROLLMENT/22) - Math.ceil(ENROLLMENT/24)} teaching sections across the district through attrition or targeted RIF. At or near the upper end of typical suburban MA class sizes.`,
    savingsMin: CS_24.min, savingsMax: CS_24.max,
    classSizeTarget: 24,
    notes: 'Still within most union contract limits. Usually accomplished through not backfilling retirements.',
  },
  {
    id: 'classsize-25',
    tier: 2, priority: 59,
    category: 'Class Size',
    label: 'Increase class size: 24 → 25 students',
    detail: `Each additional student per class across the district eliminates ~${Math.ceil(ENROLLMENT/24) - Math.ceil(ENROLLMENT/25)} more sections. 25 is the cap in many MA union contracts.`,
    savingsMin: CS_25.min, savingsMax: CS_25.max,
    classSizeTarget: 25,
    flag: 'negotiation',
    notes: 'Many MTA contracts cap at 25. Crossing this threshold typically triggers union grievances.',
  },
  {
    id: 'cut-paras',
    tier: 2, priority: 61,
    category: 'Staffing',
    label: 'Cut 5–8 non-mandated paraprofessionals',
    detail: 'General ed classroom aides, library aides, lunch monitors. IEP-mandated paras cannot be cut.',
    savingsMin: 175_000, savingsMax: 380_000,
    flag: 'legal',
    notes: 'Only non-IEP positions are eligible. Cutting IEP-mandated paras triggers IDEA due process.',
  },
  {
    id: 'cut-jv-sports',
    tier: 2, priority: 63,
    category: 'Athletics',
    label: 'Cut JV & freshman sports',
    detail: 'Eliminate JV programs in lower-participation sports (golf, tennis, gymnastics). Merge freshman into JV.',
    savingsMin: 60_000, savingsMax: 120_000,
  },
  {
    id: 'cut-instructional-coaches',
    tier: 2, priority: 66,
    category: 'Staffing',
    label: 'Cut instructional coaches',
    detail: 'Eliminate district-level coaches who support classroom teachers in literacy, math, or STEM.',
    savingsMin: 90_000, savingsMax: 220_000,
    notes: '1–2 coaching positions at $90k–$110k each.',
  },
  {
    id: 'cut-nurse-shared',
    tier: 2, priority: 68,
    category: 'Staffing',
    label: 'Share nurse across buildings',
    detail: 'Shift from one nurse per building to one nurse covering two smaller buildings on alternating days.',
    savingsMin: 40_000, savingsMax: 65_000,
    flag: 'warning',
    notes: 'MA law requires nurse coverage during school hours — often means a health aide covers the off-days.',
  },
  {
    id: 'cut-transportation',
    tier: 2, priority: 70,
    category: 'Transportation',
    label: 'Reduce non-mandated transportation routes',
    detail: 'Eliminate routes for students within walk-distance thresholds (2 mi HS / 1.5 mi MS / 1 mi elementary).',
    savingsMin: 100_000, savingsMax: 300_000,
    flag: 'warning',
    notes: 'Disproportionately affects families without cars or in unsafe walking areas.',
  },
  {
    id: 'cut-elem-language',
    tier: 2, priority: 72,
    category: 'Curriculum',
    label: 'Eliminate elementary world language (Spanish)',
    detail: 'Cut the K–5 Spanish program. Students begin world language in middle school only.',
    savingsMin: 85_000, savingsMax: 130_000,
    notes: 'Research strongly supports early language exposure. Commonly cut despite this.',
  },
  {
    id: 'cut-sro',
    tier: 2, priority: 74,
    category: 'Administration',
    label: 'Remove SRO from school budget',
    detail: "Shift school resource officer funding to the town police budget, or end the program.",
    savingsMin: 85_000, savingsMax: 110_000,
    flag: 'warning',
    notes: 'Many MA districts have moved SROs to the town budget rather than eliminating the position.',
  },
  {
    id: 'cut-kindergarten-fullday',
    tier: 2, priority: 76,
    category: 'Programs',
    label: 'Reduce full-day kindergarten to half-day',
    detail: 'Cut afternoon kindergarten. Families needing full-day care would pay tuition for extended time.',
    savingsMin: 85_000, savingsMax: 110_000,
    flag: 'warning',
    notes: 'High family impact. Research strongly favors full-day kindergarten for school readiness.',
  },

  // ── TIER 3: Crisis Mode ───────────────────────────────────────────────────
  {
    id: 'cut-social-workers',
    tier: 3, priority: 80,
    category: 'Staffing',
    label: 'Cut 2–4 school social workers / counselors',
    detail: 'Non-SPED counselors and adjustment counselors. DESE recommends 1:250; cuts push ratio to 1:500+.',
    savingsMin: 150_000, savingsMax: 380_000,
    flag: 'warning',
    notes: 'High reputational and student mental health risk. Significant community pushback.',
  },
  // Class size now crossing into crisis territory
  {
    id: 'classsize-27',
    tier: 3, priority: 82,
    category: 'Class Size',
    label: 'Increase class size: 25 → 27 students',
    detail: `Eliminates ~${Math.ceil(ENROLLMENT/25) - Math.ceil(ENROLLMENT/27)} more sections. Pushes beyond most contract limits. Requires renegotiation or a signed MOU with the teachers union.`,
    savingsMin: CS_27.min, savingsMax: CS_27.max,
    classSizeTarget: 27,
    flag: 'negotiation',
    notes: 'Exceeds most MTA contract caps. Likely to generate grievances and morale issues.',
  },
  {
    id: 'cut-asst-principal',
    tier: 3, priority: 84,
    category: 'Administration',
    label: 'Eliminate an assistant principal',
    detail: 'Cut an AP role at the elementary or middle school. Increase principal span of control.',
    savingsMin: 110_000, savingsMax: 130_000,
  },
  {
    id: 'cut-dept-heads',
    tier: 3, priority: 86,
    category: 'Administration',
    label: 'Eliminate department head stipends',
    detail: '$5k–$12k stipends per head. 12–20 district-wide. Increases teaching loads for those who remain.',
    savingsMin: 60_000, savingsMax: 240_000,
    flag: 'negotiation',
  },
  {
    id: 'classsize-28',
    tier: 3, priority: 87,
    category: 'Class Size',
    label: 'Increase class size: 27 → 28 students',
    detail: `Each additional increment eliminates ~${Math.ceil(ENROLLMENT/27) - Math.ceil(ENROLLMENT/28)} more sections. At 28 students, teacher workload is measurably above recommended levels.`,
    savingsMin: CS_28.min, savingsMax: CS_28.max,
    classSizeTarget: 28,
    flag: 'negotiation',
  },
  {
    id: 'cut-ap-courses',
    tier: 3, priority: 88,
    category: 'Curriculum',
    label: 'Eliminate low-enrollment AP & honors sections',
    detail: 'Cut AP Art History, AP Environmental Science, Latin, and other low-enrollment electives.',
    savingsMin: 85_000, savingsMax: 210_000,
    notes: '1–2 sections = $85k–$105k each. Affects college-bound students and DESE accountability profile.',
  },
  {
    id: 'rif-teachers',
    tier: 3, priority: 90,
    category: 'Staffing',
    label: 'RIF 5 teachers (Reduction in Force)',
    detail: 'Lay off 5 teachers via seniority (last in, first out). MA requires April 15 notice for following year.',
    savingsMin: 425_000, savingsMax: 525_000,
    flag: 'negotiation',
    notes: 'Seniority-based — typically cuts newest teachers first. High grievance risk.',
  },
  {
    id: 'cut-custodial',
    tier: 3, priority: 91,
    category: 'Operations',
    label: 'Cut 2–3 custodial / maintenance positions',
    detail: 'Cut third-shift custodians, reduce grounds crew. Buildings become visibly under-maintained.',
    savingsMin: 100_000, savingsMax: 195_000,
    notes: 'Deferred maintenance compounds significantly year over year.',
  },
  {
    id: 'increase-teaching-load',
    tier: 3, priority: 92,
    category: 'Staffing',
    label: 'Increase teaching loads (reduce prep periods)',
    detail: 'Require teachers to cover one additional section per day, reducing prep time. Enables fewer FTEs.',
    savingsMin: 170_000, savingsMax: 340_000,
    flag: 'negotiation',
    notes: 'Contracts specify prep time. Requires renegotiation or MOU. Significant morale impact.',
  },
  {
    id: 'classsize-30',
    tier: 3, priority: 93,
    category: 'Class Size',
    label: 'Increase class size: 28 → 30 students',
    detail: `Eliminates ~${Math.ceil(ENROLLMENT/28) - Math.ceil(ENROLLMENT/30)} more sections. At 30 students, research documents measurable declines in learning outcomes, particularly in K–3.`,
    savingsMin: CS_30.min, savingsMax: CS_30.max,
    classSizeTarget: 30,
    flag: 'negotiation',
    notes: 'Associated with measurable learning outcome decline. Generates regulatory scrutiny from DESE.',
  },
  {
    id: 'cut-psychologist',
    tier: 3, priority: 94,
    category: 'Staffing',
    label: 'Reduce school psychologist services',
    detail: 'Cut non-mandated psychologist hours or eliminate a part-time position.',
    savingsMin: 50_000, savingsMax: 120_000,
    flag: 'legal',
    notes: 'IDEA-mandated evaluations cannot be reduced. Only non-evaluation/consultation hours are cuttable.',
  },
  {
    id: 'outsource-custodial',
    tier: 3, priority: 95,
    category: 'Operations',
    label: 'Outsource custodial services',
    detail: 'Replace district-employed custodians with a contracted cleaning company. Net savings after contract costs.',
    savingsMin: 100_000, savingsMax: 200_000,
    flag: 'negotiation',
    notes: 'Quality and responsiveness often decline. Union contract buyout required.',
  },
  {
    id: 'furlough-days',
    tier: 3, priority: 96,
    category: 'Staffing',
    label: 'Furlough days — 5 days, all staff',
    detail: 'Reduce school year by 5 days, applying a ~2.7% salary reduction across the entire workforce.',
    savingsMin: 350_000, savingsMax: 450_000,
    flag: 'negotiation',
    notes: 'Rare in Massachusetts. Legally complex under MTA contracts. Used only in genuine fiscal crisis.',
  },
  {
    id: 'classsize-33',
    tier: 3, priority: 97,
    category: 'Class Size',
    label: 'Increase class size: 30 → 33 students',
    detail: `Eliminates ~${Math.ceil(ENROLLMENT/30) - Math.ceil(ENROLLMENT/33)} more sections. 33 students per class is considered crisis level. Triggers DESE scrutiny and is associated with significant educational harm.`,
    savingsMin: CS_33.min, savingsMax: CS_33.max,
    classSizeTarget: 33,
    flag: 'negotiation',
    notes: 'Crisis / last resort. Typically seen only in districts under state fiscal oversight.',
  },
  {
    id: 'share-superintendent',
    tier: 3, priority: 98,
    category: 'Administration',
    label: 'Share superintendent with another district',
    detail: 'Enter a shared services agreement. Superintendent splits time 50/50 with a neighboring district.',
    savingsMin: 60_000, savingsMax: 100_000,
    flag: 'warning',
    notes: 'Reduces superintendent availability and institutional focus. Used in very small MA districts.',
  },
  {
    id: 'consolidate-building',
    tier: 3, priority: 99,
    category: 'Administration',
    label: 'Consolidate / close a school building',
    detail: 'Merge two elementary schools into one building. Eliminates a principal, office staff, and building costs.',
    savingsMin: 200_000, savingsMax: 400_000,
    flag: 'warning',
    notes: 'Very high community resistance. Requires approval and a significant transition plan.',
  },
]

// ── Auto-selection algorithm ──────────────────────────────────────────────────
// Greedy: pick cuts in priority order until deficit is covered.

function autoSelectCuts(deficit: number, cuts: CutOption[]): Set<string> {
  const sorted = [...cuts].sort((a, b) => a.priority - b.priority)
  const selected = new Set<string>()
  let remaining = deficit
  for (const cut of sorted) {
    if (remaining <= 0) break
    selected.add(cut.id)
    remaining -= Math.round((cut.savingsMin + cut.savingsMax) / 2)
  }
  return selected
}

// ── Tier metadata ─────────────────────────────────────────────────────────────

type TierMeta = { label: string; subtitle: string; rangeLabel: string; bg: string; border: string; text: string; badge: string; dot: string }

const TIER_META: Record<Tier, TierMeta> = {
  1: {
    label: 'Tier 1 — Low Impact', subtitle: 'Nearly invisible to students. Politically easy.',
    rangeLabel: 'Typical at $0–$1M deficit',
    bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800',
    badge: 'bg-green-100 text-green-700', dot: 'bg-green-500',
  },
  2: {
    label: 'Tier 2 — Visible Cuts', subtitle: 'Parents start noticing. Educational quality begins to erode.',
    rangeLabel: 'Typical at $1M–$2M deficit',
    bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500',
  },
  3: {
    label: 'Tier 3 — Crisis Mode', subtitle: 'Real educational harm. Community conflict and union grievances.',
    rangeLabel: 'Typical at $2M–$5M deficit',
    bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800',
    badge: 'bg-red-100 text-red-700', dot: 'bg-red-500',
  },
}

const FLAG_META: Record<CutFlag, { label: string; color: string }> = {
  negotiation: { label: 'Requires contract negotiation', color: 'bg-purple-100 text-purple-700' },
  legal:       { label: 'IEP/IDEA legal exposure', color: 'bg-orange-100 text-orange-700' },
  warning:     { label: 'High community / equity impact', color: 'bg-rose-100 text-rose-700' },
}

const CATEGORY_STYLE: Record<string, string> = {
  Staffing:       'bg-blue-100 text-blue-700',
  Athletics:      'bg-cyan-100 text-cyan-700',
  Administration: 'bg-violet-100 text-violet-700',
  Transportation: 'bg-teal-100 text-teal-700',
  Curriculum:     'bg-indigo-100 text-indigo-700',
  Operations:     'bg-gray-100 text-gray-600',
  Programs:       'bg-orange-100 text-orange-700',
  'Class Size':   'bg-slate-700 text-white',
}

const PRESETS = [
  { label: '$500K',  amount: 500_000,   hint: 'Small — manageable with Tier 1 cuts only' },
  { label: '$1.2M',  amount: 1_200_000, hint: 'Moderate — spills into Tier 2 cuts' },
  { label: '$2M',    amount: 2_000_000, hint: 'Significant — deep Tier 2 and early Tier 3' },
  { label: '$3.5M',  amount: 3_500_000, hint: 'Crisis — major RIF and program elimination' },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function CutLinePage() {
  const { data }        = useBudgetData()
  const { primaryYear } = useBudgetStore()

  // Lunenburg's actual gap from Prop 2½ data
  const lunenGap = useMemo(() => {
    if (!data) return null
    const idx = data.years.findIndex(y => y.key === primaryYear)
    const compareYear = idx > 0 ? data.years[idx - 1].key : data.years[0].key
    const m = computeProp25(data, primaryYear, compareYear)
    return {
      amount:        m.overrideAmount ?? m.dollarAboveCap,
      isOverride:    m.overrideAmount != null,
      requestedTotal: m.requestedTotal,
      townManagerTotal: m.townManagerTotal,
      primaryLabel:  data.years.find(y => y.key === primaryYear)?.label ?? primaryYear,
    }
  }, [data, primaryYear])

  const defaultDeficit = useMemo(() => {
    if (!lunenGap || !lunenGap.amount || lunenGap.amount <= 0) return 1_200_000
    return Math.round(lunenGap.amount / 50_000) * 50_000
  }, [lunenGap])

  const [deficitOverride, setDeficitOverride] = useState<number | null>(null)
  const activeDeficit = deficitOverride ?? defaultDeficit

  const budgetTotal = useMemo(() => data?.grandTotals[primaryYear] ?? null, [data, primaryYear])

  // Auto-select cuts based on deficit
  const triggered = useMemo(() => autoSelectCuts(activeDeficit, CUT_OPTIONS), [activeDeficit])

  // Highest triggered class size
  const currentClassSize = useMemo(() => {
    let max = BASE_CLASS_SIZE
    for (const cut of CUT_OPTIONS) {
      if (triggered.has(cut.id) && cut.classSizeTarget != null) {
        max = Math.max(max, cut.classSizeTarget)
      }
    }
    return max
  }, [triggered])

  // Savings totals
  const totalSavings = useMemo(() => {
    let sum = 0
    for (const cut of CUT_OPTIONS) {
      if (triggered.has(cut.id)) sum += Math.round((cut.savingsMin + cut.savingsMax) / 2)
    }
    return sum
  }, [triggered])

  const remaining    = activeDeficit - totalSavings
  const covered      = remaining <= 0
  const coveragePct  = activeDeficit > 0 ? Math.min(100, (totalSavings / activeDeficit) * 100) : 0

  // Sorted cuts for finding the cut-line position
  const sortedIds = useMemo(
    () => [...CUT_OPTIONS].sort((a, b) => a.priority - b.priority).map(c => c.id),
    [],
  )
  const firstUntriggeredId = sortedIds.find(id => !triggered.has(id)) ?? null

  // Cuts grouped by tier, in priority order
  const cutsByTier = useMemo(() => {
    const sorted = [...CUT_OPTIONS].sort((a, b) => a.priority - b.priority)
    return {
      1: sorted.filter(c => c.tier === 1),
      2: sorted.filter(c => c.tier === 2),
      3: sorted.filter(c => c.tier === 3),
    } as Record<Tier, CutOption[]>
  }, [])

  const lunenAmount = lunenGap?.amount
  const lunenMarkerPct = lunenAmount && lunenAmount > 0 && lunenAmount <= 5_000_000
    ? (lunenAmount / 5_000_000) * 100
    : null

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 pb-24 space-y-6 max-w-4xl">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Budget Stress Explorer</h1>
        <p className="mt-1 text-sm text-gray-500">
          Drag the deficit slider to see which cuts a school district typically makes at each funding level.
          Cuts trigger automatically in the order districts historically reach them — and class sizes increase
          right alongside them. Based on documented Massachusetts suburban district patterns (2024–2025).
        </p>
      </div>

      {/* Lunenburg position callout */}
      {lunenGap && lunenAmount != null && lunenAmount > 0 && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 flex items-start gap-4">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-blue-900">
              Lunenburg's current position — {lunenGap.primaryLabel}
            </p>
            <p className="text-sm text-blue-700 mt-0.5">
              <span className="font-bold">${lunenAmount.toLocaleString()}</span>
              {lunenGap.isOverride
                ? ' gap between school request and Town Manager approved budget — what voters would need to fund via override, or what gets cut if they don\'t.'
                : ' above the Prop 2½ cap — structural gap the district must address.'}
            </p>
          </div>
          <button
            onClick={() => setDeficitOverride(Math.round(lunenAmount / 50_000) * 50_000)}
            className="flex-shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            Reset to this
          </button>
        </div>
      )}

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-2">
        {PRESETS.map(p => (
          <button
            key={p.amount}
            onClick={() => setDeficitOverride(p.amount)}
            title={p.hint}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              activeDeficit === p.amount
                ? 'bg-blue-600 text-white border-blue-600 font-medium'
                : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Deficit slider */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Deficit to close</p>
          {budgetTotal && (
            <span className="text-xs text-gray-400">
              {((activeDeficit / budgetTotal) * 100).toFixed(1)}% of {data?.years.find(y => y.key === primaryYear)?.short ?? ''} budget
            </span>
          )}
        </div>
        <p className="text-4xl font-bold text-gray-900 mb-5">
          ${activeDeficit.toLocaleString()}
        </p>
        <div className="relative pb-6">
          <input
            type="range"
            min={0} max={5_000_000} step={50_000}
            value={activeDeficit}
            onChange={e => setDeficitOverride(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
          {lunenMarkerPct != null && (
            <div
              className="absolute top-0 flex flex-col items-center pointer-events-none"
              style={{ left: `${lunenMarkerPct}%`, transform: 'translateX(-50%)' }}
            >
              <div className="w-0.5 h-5 bg-blue-500 mt-1" />
              <span className="text-xs text-blue-600 font-semibold whitespace-nowrap mt-0.5">
                ← Lunenburg now
              </span>
            </div>
          )}
        </div>
        <div className="flex justify-between text-xs text-gray-400">
          <span>$0</span><span>$1M</span><span>$2M</span><span>$3M</span><span>$4M</span><span>$5M</span>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Cuts triggered</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{triggered.size}</p>
          <p className="text-xs text-gray-400">of {CUT_OPTIONS.length} tracked</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Savings covered</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">${(totalSavings / 1000).toFixed(0)}K</p>
          <p className="text-xs text-gray-400">{Math.round(coveragePct)}% of target</p>
        </div>
        <div className={`rounded-xl border p-4 ${covered ? 'border-green-200 bg-green-50' : 'border-red-100 bg-red-50'}`}>
          <p className={`text-xs font-semibold uppercase tracking-wide ${covered ? 'text-green-500' : 'text-red-400'}`}>
            {covered ? 'Surplus' : 'Still unaddressed'}
          </p>
          <p className={`text-2xl font-bold mt-1 ${covered ? 'text-green-700' : 'text-red-600'}`}>
            ${(Math.abs(remaining) / 1000).toFixed(0)}K
          </p>
          <p className={`text-xs ${covered ? 'text-green-500' : 'text-red-400'}`}>
            {covered ? 'fully covered' : 'gap remaining'}
          </p>
        </div>
        <div className={`rounded-xl border p-4 ${
          currentClassSize <= 24 ? 'border-green-200 bg-green-50' :
          currentClassSize <= 27 ? 'border-amber-200 bg-amber-50' :
          'border-red-200 bg-red-50'
        }`}>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Class size</p>
          <p className={`text-2xl font-bold mt-1 ${
            currentClassSize <= 24 ? 'text-green-700' :
            currentClassSize <= 27 ? 'text-amber-700' :
            'text-red-700'
          }`}>{currentClassSize}</p>
          <p className="text-xs text-gray-400">students / class</p>
        </div>
      </div>

      {/* Cut tiers */}
      {([1, 2, 3] as Tier[]).map(tier => {
        const meta      = TIER_META[tier]
        const tierCuts  = cutsByTier[tier]
        const nTriggered = tierCuts.filter(c => triggered.has(c.id)).length

        return (
          <div key={tier} className={`rounded-xl border ${meta.border} overflow-hidden`}>
            {/* Tier header */}
            <div className={`${meta.bg} px-5 py-3 flex items-start justify-between gap-4`}>
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5 ${meta.dot}`} />
                <div>
                  <p className={`text-sm font-semibold ${meta.text}`}>{meta.label}</p>
                  <p className={`text-xs mt-0.5 ${meta.text} opacity-70`}>{meta.subtitle}</p>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.badge}`}>
                  {meta.rangeLabel}
                </span>
                {nTriggered > 0 && (
                  <p className={`text-xs font-medium ${meta.text} mt-1`}>
                    {nTriggered} of {tierCuts.length} triggered
                  </p>
                )}
              </div>
            </div>

            {/* Cut rows */}
            <div className="divide-y divide-gray-100">
              {tierCuts.map(cut => {
                const isTriggered     = triggered.has(cut.id)
                const isCutLineHere   = cut.id === firstUntriggeredId
                const isClassSizeRow  = cut.classSizeTarget != null

                return (
                  <div key={cut.id}>
                    {/* Cut line divider */}
                    {isCutLineHere && (
                      <div className="flex items-center gap-3 px-5 py-2 bg-gray-50 border-y border-dashed border-gray-300">
                        <div className="flex-1 h-px bg-gray-300" />
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
                          ✂ Cut line — cuts below not yet triggered
                        </span>
                        <div className="flex-1 h-px bg-gray-300" />
                      </div>
                    )}

                    <div className={`flex items-start gap-4 px-5 py-4 transition-colors ${
                      isTriggered
                        ? isClassSizeRow
                          ? 'bg-slate-50'
                          : 'bg-blue-50'
                        : 'bg-white opacity-50'
                    }`}>
                      {/* Status indicator */}
                      <div className="flex-shrink-0 mt-0.5">
                        {isTriggered ? (
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center ${
                            isClassSizeRow ? 'bg-slate-600' : 'bg-blue-600'
                          }`}>
                            <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center flex-wrap gap-1.5">
                            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${CATEGORY_STYLE[cut.category] ?? 'bg-gray-100 text-gray-600'}`}>
                              {cut.category}
                            </span>
                            <span className={`text-sm font-medium ${isTriggered ? (isClassSizeRow ? 'text-slate-900' : 'text-blue-900') : 'text-gray-500'}`}>
                              {cut.label}
                            </span>
                            {isTriggered && (
                              <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${
                                isClassSizeRow ? 'bg-slate-200 text-slate-700' : 'bg-blue-100 text-blue-700'
                              }`}>
                                triggered
                              </span>
                            )}
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className={`text-sm font-semibold whitespace-nowrap ${isTriggered ? 'text-gray-800' : 'text-gray-400'}`}>
                              ${(cut.savingsMin / 1000).toFixed(0)}k – ${(cut.savingsMax / 1000).toFixed(0)}k
                            </p>
                            <p className="text-xs text-gray-400">
                              {isClassSizeRow ? 'incremental savings' : 'est. savings'}
                            </p>
                          </div>
                        </div>
                        <p className={`text-xs mt-1.5 ${isTriggered ? 'text-gray-600' : 'text-gray-400'}`}>
                          {cut.detail}
                        </p>
                        {isTriggered && (cut.flag || cut.notes) && (
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            {cut.flag && (
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLAG_META[cut.flag].color}`}>
                                ⚠ {FLAG_META[cut.flag].label}
                              </span>
                            )}
                            {cut.notes && (
                              <span className="text-xs text-gray-400 italic">{cut.notes}</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Disclaimer */}
      <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
        <p className="text-xs text-gray-400 leading-relaxed">
          <span className="font-medium text-gray-500">About this tool:</span> Cut order is based on documented
          patterns from Massachusetts suburban districts (2024–2025). Real sequencing varies by district, union
          contracts, and school committee priorities. Class size savings assume ~1,750 enrolled K–12 students
          and $95,000 average fully-loaded teacher cost. Lunenburg's gap is drawn from the Prop 2½ analysis
          in the budget data. This is a community education tool — not a budget recommendation.
        </p>
      </div>

      {/* Sticky bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 md:left-56 z-20 bg-white border-t border-gray-200 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-500">
                {triggered.size} cut{triggered.size !== 1 ? 's' : ''} triggered
                {currentClassSize > BASE_CLASS_SIZE ? ` · class size → ${currentClassSize}` : ''}
              </span>
              <span className="text-xs text-gray-400">target: ${activeDeficit.toLocaleString()}</span>
            </div>
            <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${covered ? 'bg-green-500' : 'bg-blue-500'}`}
                style={{ width: `${coveragePct}%` }}
              />
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className={`text-xl font-bold leading-none ${covered ? 'text-green-700' : 'text-gray-900'}`}>
              ${totalSavings.toLocaleString()}
            </p>
            <p className={`text-xs mt-0.5 ${covered ? 'text-green-600 font-medium' : 'text-red-500'}`}>
              {covered ? `+$${Math.abs(remaining).toLocaleString()} surplus` : `$${remaining.toLocaleString()} remaining`}
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
