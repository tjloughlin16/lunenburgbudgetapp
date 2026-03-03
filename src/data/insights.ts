import type { BudgetData, FiscalYear, CategoryCode, Section } from './types'
import { CATEGORY_LABELS, CATEGORY_DESCRIPTIONS } from './types'
import { formatDollar, formatPct } from './transforms'

export type InsightType = 'increase' | 'decrease' | 'neutral' | 'hero'

// ── Budget narrative story ────────────────────────────────────────────────────

export interface BudgetStory {
  paragraphs: string[]       // each entry = one rendered paragraph
  primaryLabel: string
  compareLabel: string
}

export function computeBudgetStory(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): BudgetStory {
  const { groups, lineItems, grandTotals, sections, years } = data

  const primaryLabel = years.find(y => y.key === primaryYear)?.label ?? primaryYear.toUpperCase()
  const compareLabel = years.find(y => y.key === compareYear)?.label ?? compareYear.toUpperCase()
  const primaryShort = years.find(y => y.key === primaryYear)?.short ?? primaryYear.toUpperCase()

  const totalPrimary   = grandTotals[primaryYear] ?? 0
  const totalCompare   = grandTotals[compareYear] ?? 0
  const freeCashAdjust = data.freeCash[compareYear] ?? 0
  const adjustedBase   = totalCompare + freeCashAdjust  // actual prior-year levy
  const totalDelta     = totalPrimary - adjustedBase    // levy delta
  const totalPctChange = pct(adjustedBase, totalPrimary)

  // Salary totals
  const salPrimary = sections.salaries.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
  const salCompare = sections.salaries.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
  const salDelta = salPrimary - salCompare
  const salPct = pct(salCompare, salPrimary)
  const salShare = totalPrimary > 0 ? Math.round((salPrimary / totalPrimary) * 100) : 0
  const salSharePrev = totalCompare > 0 ? Math.round((salCompare / totalCompare) * 100) : 0

  // Expense totals
  const expPrimary = sections.expenses.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
  const expCompare = sections.expenses.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
  const expDelta = expPrimary - expCompare

  // Group-level deltas
  const groupDeltas = groups.filter(g => g.section !== 'summary').map(g => ({
    ...g, cleanName: cleanLabel(g.label),
    a: g.totals[compareYear] ?? 0,
    b: g.totals[primaryYear] ?? 0,
    delta: (g.totals[primaryYear] ?? 0) - (g.totals[compareYear] ?? 0),
  }))

  const topCuts = [...groupDeltas].filter(g => g.delta < -5_000).sort((a, b) => a.delta - b.delta)

  // Instructional spending (category 2)
  const instrGroups = groups.filter(g => g.categoryCode === '2')
  const instrPrimary = instrGroups.reduce((s, g) => s + (g.totals[primaryYear] ?? 0), 0)
  const instrCompare = instrGroups.reduce((s, g) => s + (g.totals[compareYear] ?? 0), 0)
  const instrDelta = instrPrimary - instrCompare
  const instrPct = pct(instrCompare, instrPrimary)
  const instrShare = totalPrimary > 0 ? Math.round((instrPrimary / totalPrimary) * 100) : 0

  // Student services (category 3 — special ed, counseling, transportation)
  const ssGroups = groups.filter(g => g.categoryCode === '3')
  const ssPrimary = ssGroups.reduce((s, g) => s + (g.totals[primaryYear] ?? 0), 0)
  const ssCompare = ssGroups.reduce((s, g) => s + (g.totals[compareYear] ?? 0), 0)
  const ssDelta = ssPrimary - ssCompare

  // Fixed costs (category 5 — insurance, retirement)
  const fcGroups = groups.filter(g => g.categoryCode === '5')
  const fcPrimary = fcGroups.reduce((s, g) => s + (g.totals[primaryYear] ?? 0), 0)
  const fcCompare = fcGroups.reduce((s, g) => s + (g.totals[compareYear] ?? 0), 0)
  const fcDelta = fcPrimary - fcCompare
  const fcPct = pct(fcCompare, fcPrimary)

  // Historical average
  const nonProjected = years.filter(y => !y.isProjected)
  const yearOverYearChanges: number[] = []
  for (let i = 1; i < nonProjected.length; i++) {
    const p2 = pct(grandTotals[nonProjected[i - 1].key] ?? 0, grandTotals[nonProjected[i].key] ?? 0)
    if (p2 !== null) yearOverYearChanges.push(p2)
  }
  const historicalAvg = yearOverYearChanges.length >= 2
    ? yearOverYearChanges.reduce((s, c) => s + c, 0) / yearOverYearChanges.length
    : null

  // Fastest-growing line item (for a concrete "spotlight" detail)
  const lineSpotlight = lineItems
    .filter(i => !i.isGroupHeader && i.section !== 'summary')
    .map(i => {
      const a = i.values[compareYear] ?? 0
      const b = i.values[primaryYear] ?? 0
      return { ...i, a, b, delta: b - a, pctChange: a > 5_000 && b > a ? (b - a) / a : null }
    })
    .filter(i => i.pctChange !== null && i.delta > 15_000)
    .sort((a, b) => b.pctChange! - a.pctChange!)[0] ?? null

  // ── Per-school totals (line-item attribution, same logic as computeSchoolBreakdown) ──
  const glMap = new Map(groups.map(g => [g.code, g.label]))
  function storySchoolKey(text: string): string | null {
    const t = text.replace(/^\d+\s*[-–]\s*/, '').trim()
    const m = t.match(/^([A-Z]\.[A-Z]\.)\s/)
    if (m) return m[1].replace(/\./g, '').toLowerCase()
    if (/^Primary\s+School\b/i.test(t))     return 'ps'
    if (/^Elementary\s+School\b/i.test(t))  return 'es'
    if (/^Middle\s+School\b/i.test(t))      return 'ms'
    if (/^High\s+School\b/i.test(t))        return 'hs'
    return null
  }
  const schoolTotMap = new Map<string, { primary: number; compare: number }>()
  for (const item of lineItems) {
    if (item.isGroupHeader || item.section === 'summary') continue
    const a = item.values[compareYear] ?? 0
    const b = item.values[primaryYear] ?? 0
    if (a === 0 && b === 0) continue
    const parentLabel = item.parentCode ? (glMap.get(item.parentCode) ?? '') : ''
    const sk = storySchoolKey(item.description) ?? storySchoolKey(parentLabel)
    if (!sk) continue
    if (!schoolTotMap.has(sk)) schoolTotMap.set(sk, { primary: 0, compare: 0 })
    const t = schoolTotMap.get(sk)!
    t.primary += b; t.compare += a
  }
  const SCHOOL_FULL: Record<string, string> = {
    ps: 'Primary School', es: 'Elementary School', ms: 'Middle School', hs: 'High School',
  }
  const schoolList = (['ps', 'es', 'ms', 'hs'] as const)
    .filter(k => schoolTotMap.has(k))
    .map(k => {
      const t = schoolTotMap.get(k)!
      return { key: k, name: SCHOOL_FULL[k], primary: t.primary, compare: t.compare,
               delta: t.primary - t.compare, pctChange: pct(t.compare, t.primary) }
    })

  // ── Athletics totals ──────────────────────────────────────────────────────
  const athGroups = groups.filter(g => g.code.startsWith('3510') || g.code.startsWith('3520'))
  const athPrimary = athGroups.reduce((s, g) => s + (g.totals[primaryYear] ?? 0), 0)
  const athCompare = athGroups.reduce((s, g) => s + (g.totals[compareYear] ?? 0), 0)
  const athDelta   = athPrimary - athCompare
  const athPct     = pct(athCompare, athPrimary)

  // ── Arts / music totals (line items matching arts keywords) ───────────────
  const artsRx = /music|band|chorus|orchestra|choir|\bart\b|\barts\b|drama|theater|theatre|\bdance\b|perform/i
  const artsItems = lineItems.filter(i =>
    !i.isGroupHeader && i.section !== 'summary' && artsRx.test(i.description)
  )
  const artsPrimary = artsItems.reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
  const artsCompare = artsItems.reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
  const artsDelta   = artsPrimary - artsCompare
  const artsPct     = pct(artsCompare, artsPrimary)

  // ── Special education totals (includes out-of-district tuitions) ──────────
  const spedRx = /special ed|sped|therapeutic|paraprofessional.*spec/i
  const spedParentRx = /special ed|sped|therapeutic|curriculum\/spec/i
  const spedItems = lineItems.filter(i => {
    if (i.isGroupHeader || i.section === 'summary') return false
    const parentLabel = i.parentCode ? (glMap.get(i.parentCode) ?? '') : ''
    return spedRx.test(i.description) ||
           spedParentRx.test(parentLabel) ||
           i.parentCode?.startsWith('9300') ||   // private tuitions
           i.parentCode?.startsWith('9400')       // collaborative tuitions
  })
  const spedPrimary = spedItems.reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
  const spedCompare = spedItems.reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
  const spedDelta   = spedPrimary - spedCompare
  const spedPct     = pct(spedCompare, spedPrimary)

  const paragraphs: string[] = []

  // ── Paragraph 1: Opening — the headline number and overall direction ─────────
  {
    const parts: string[] = []
    // Use adjustedBase (levy) as the comparison anchor, with a parenthetical when free cash applies
    const compareAmt = freeCashAdjust < 0
      ? `${formatDollar(adjustedBase)} levy (${compareLabel}'s ${formatDollar(totalCompare)} gross budget less ${formatDollar(Math.abs(freeCashAdjust))} free cash)`
      : `${formatDollar(adjustedBase)}`
    if (totalDelta > 0 && totalPctChange !== null) {
      const magnitude = totalPctChange > 0.1 ? 'a significant increase' : totalPctChange > 0.05 ? 'an increase' : 'a modest increase'
      parts.push(
        `The ${primaryShort} proposed budget for Lunenburg Public Schools totals ${formatDollar(totalPrimary)} — ${magnitude} of ${formatDollar(totalDelta)} (${formatPct(totalPctChange)}) over ${compareLabel}'s ${compareAmt}.`
      )
    } else if (totalDelta < 0 && totalPctChange !== null) {
      parts.push(
        `The ${primaryShort} proposed budget for Lunenburg Public Schools totals ${formatDollar(totalPrimary)} — a reduction of ${formatDollar(Math.abs(totalDelta))} (${formatPct(totalPctChange)}) from ${compareLabel}'s ${compareAmt}.`
      )
    } else {
      parts.push(
        `The ${primaryShort} proposed budget for Lunenburg Public Schools totals ${formatDollar(totalPrimary)}, essentially flat compared to ${compareLabel}'s ${compareAmt}.`
      )
    }
    parts.push(
      `These numbers represent the real costs of educating Lunenburg students, maintaining school buildings, and employing the staff that makes it possible — and this analysis breaks down where that money comes from and where it goes.`
    )
    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 1b: Prop 2½ context ────────────────────────────────────────────
  {
    // freeCashAdjust and adjustedBase already computed above
    const levyDelta      = totalDelta   // same thing now (totalDelta = totalPrimary - adjustedBase)
    const levyPctChange  = totalPctChange
    const capAmount      = adjustedBase * 0.025
    const dollarAbove    = levyDelta - capAmount
    const pptAbove       = levyPctChange !== null ? levyPctChange - 0.025 : null
    const hasFreeCarry   = freeCashAdjust < 0

    if (levyPctChange !== null && levyPctChange > 0.025) {
      const abovePpts    = pptAbove !== null ? fmtPctMag(pptAbove) : ''
      const aboveDollars = formatDollar(dollarAbove)
      let para = `Under Massachusetts' Proposition 2½, a town's property tax levy can only grow by 2.5% per year without a voter-approved override. `

      if (hasFreeCarry) {
        // Explain the free cash complication first
        para += `${compareLabel} benefited from ${formatDollar(Math.abs(freeCashAdjust))} in one-time free cash that offset that year's budget, reducing what taxpayers were actually charged. ` +
          `Since free cash is a one-time source, it does not carry forward — meaning the ${compareLabel} levy base for Prop 2½ purposes is ${formatDollar(adjustedBase)}, not the gross budget of ${formatDollar(totalCompare)}. ` +
          `When measured from that actual levy base, the school budget is asking for a ${fmtPctMag(levyPctChange)} increase — ${abovePpts} above the cap — representing roughly ${aboveDollars} more than Prop 2½ would allow from the prior levy. ` +
          `Of that total levy increase, ${formatDollar(Math.abs(freeCashAdjust))} simply replaces the free cash that can no longer be used, and ${formatDollar(levyDelta - Math.abs(freeCashAdjust))} reflects genuinely new spending.`
      } else {
        para += `The proposed school budget is up ${levyPctChange !== null ? formatPct(levyPctChange) : ''} — ${abovePpts} above that cap, representing roughly ${aboveDollars} more than the 2.5% threshold would allow. `
      }

      para += ` This does not automatically mean an override is required: Prop 2½ applies to the entire town levy, not the school budget alone, and increases in state aid can offset some of the pressure. However, it signals that school spending may be putting upward pressure on the town's levy limit, and residents should watch for override discussion at Town Meeting.`
      paragraphs.push(para)

    } else if (levyPctChange !== null && levyPctChange >= 0) {
      let para = `Under Massachusetts' Proposition 2½, a town's property tax levy can only grow by 2.5% per year without a voter-approved override. `
      if (hasFreeCarry) {
        para += `${compareLabel} used ${formatDollar(Math.abs(freeCashAdjust))} in one-time free cash, so the actual levy base for Prop 2½ purposes is ${formatDollar(adjustedBase)}. ` +
          `Even accounting for that adjustment, the proposed levy increase of ${fmtPctMag(levyPctChange)} remains within the 2.5% cap — the school budget growth does not appear to create override pressure this year. `
      } else {
        para += `The proposed school budget increase of ${formatPct(levyPctChange)} falls within that cap, meaning the school budget growth alone does not appear to create override pressure this year. `
      }
      para += `The full picture depends on the rest of the town budget and any changes in state aid.`
      paragraphs.push(para)
    }
    // If budget is shrinking, skip this paragraph entirely
  }

  // ── Paragraph 2: Personnel costs — always the dominant story ────────────────
  {
    const parts: string[] = []
    parts.push(
      `The single largest factor in any school budget is people, and this year is no exception.`
    )
    if (salShare === salSharePrev) {
      parts.push(
        `Salaries and compensation account for ${salShare} cents of every dollar in this budget — unchanged from last year — totaling ${formatDollar(salPrimary)}.`
      )
    } else {
      parts.push(
        `Salaries and compensation account for ${salShare} cents of every dollar in this budget, ${salShare > salSharePrev ? 'up' : 'down'} from ${salSharePrev} cents last year, totaling ${formatDollar(salPrimary)}.`
      )
    }
    if (salDelta > 0) {
      // Find the top salary-section group increase for a specific call-out
      const topSalGroup = [...groupDeltas]
        .filter(g => g.section === 'salaries' && g.delta > 0)
        .sort((a, b) => b.delta - a.delta)[0]
      if (topSalGroup && Math.abs(salDelta) > 0.005) {
        parts.push(
          `Compensation is up ${formatDollar(salDelta)}${salPct !== null ? ` (${formatPct(salPct)})` : ''} overall, with ${topSalGroup.cleanName} representing the largest single increase at ${formatDollar(topSalGroup.delta)}.`
        )
      } else {
        parts.push(`Overall compensation costs are up ${formatDollar(salDelta)}${salPct !== null ? ` (${formatPct(salPct)})` : ''}.`)
      }
      parts.push(
        `These increases likely reflect contractual obligations, cost-of-living adjustments, and in some cases new positions added to meet growing student needs.`
      )
    } else if (salDelta < 0) {
      parts.push(
        `Personnel costs have decreased by ${formatDollar(Math.abs(salDelta))}, suggesting staffing adjustments tied to enrollment changes or budget constraints.`
      )
    }
    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 3: Other cost drivers ─────────────────────────────────────────
  {
    const parts: string[] = []
    const otherDrivers: string[] = []

    // Fixed costs (insurance, retirement)
    if (Math.abs(fcDelta) > 10_000) {
      const dir = fcDelta > 0 ? 'risen' : 'fallen'
      const desc = fcDelta > 0
        ? `driven largely by increases in health insurance premiums and retirement contributions — costs the district does not control`
        : `reflecting a favorable change in insurance rates or benefit structures`
      otherDrivers.push(`fixed costs such as health insurance and retirement benefits have ${dir} by ${formatDollar(Math.abs(fcDelta))}${fcPct !== null ? ` (${formatPct(fcPct)})` : ''}, ${desc}`)
    }

    // Student services / special ed
    if (Math.abs(ssDelta) > 10_000) {
      const dir = ssDelta > 0 ? 'increased' : 'decreased'
      const context = ssDelta > 0
        ? `these services — including special education, counseling, and transportation — are largely driven by individual student needs and legal mandates; cutting them would jeopardize federal and state compliance obligations`
        : `reflecting improved efficiencies in service delivery and transportation routing`
      otherDrivers.push(`student support services have ${dir} by ${formatDollar(Math.abs(ssDelta))} — ${context}`)
    }

    // Non-salary top increase (if not already covered by salary)
    const topNonSalIncrease = [...groupDeltas]
      .filter(g => g.section === 'expenses' && g.delta > 10_000)
      .sort((a, b) => b.delta - a.delta)[0]
    if (topNonSalIncrease && !otherDrivers.some(d => d.includes('insurance'))) {
      otherDrivers.push(`on the operating side, ${topNonSalIncrease.cleanName} is up ${formatDollar(topNonSalIncrease.delta)}, reflecting rising costs in ${topNonSalIncrease.categoryCode === '5' ? 'insurance and fixed obligations' : 'program operations and materials'}`)
    }

    if (otherDrivers.length > 0) {
      if (otherDrivers.length === 1) {
        parts.push(`Beyond salaries, ${otherDrivers[0]}.`)
      } else {
        parts.push(
          `Beyond salaries, two other areas are driving meaningful change in this budget.`,
          `First, ${otherDrivers[0]}.`,
          `Additionally, ${otherDrivers[1]}.`
        )
      }
    } else {
      // If no notable other drivers, speak to stability
      parts.push(
        `Beyond personnel, operating costs have remained relatively stable this year.`,
        `Discretionary spending appears to have been held relatively flat while core programs remained funded.`
      )
    }

    // Spotlight a dramatic line-item change if there is one
    if (lineSpotlight && lineSpotlight.pctChange !== null && lineSpotlight.pctChange > 0.5) {
      const parent = groups.find(g => g.code === lineSpotlight.parentCode)
      const parentName = parent ? ` within ${cleanLabel(parent.label)}` : ''
      parts.push(
        `One item worth highlighting: "${lineSpotlight.description}"${parentName} jumped from ${formatDollar(lineSpotlight.a)} to ${formatDollar(lineSpotlight.b)} — an increase of ${formatDollar(lineSpotlight.delta)} — a change that warrants attention and reflects ${lineSpotlight.delta > 50_000 ? 'a significant new commitment' : 'a targeted adjustment'} in this area.`
      )
    }
    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 4: Cuts and tradeoffs ─────────────────────────────────────────
  {
    const parts: string[] = []
    if (topCuts.length === 0) {
      parts.push(
        `Based on the budget documents, no programs appear to have been eliminated, no positions cut, and no student services reduced.`
      )
      if (expDelta < 0) {
        parts.push(`Operating expenses are slightly down ${formatDollar(Math.abs(expDelta))}, which appears to reflect efficiencies rather than cuts to student-facing programs.`)
      } else {
        parts.push(`Every program and position funded in ${compareLabel} appears to continue in this proposed budget.`)
      }
    } else {
      const totalCutAmt = topCuts.reduce((s, c) => s + c.delta, 0)
      parts.push(
        `The proposed budget reflects real tradeoffs.`
      )
      if (topCuts.length === 1) {
        const c = topCuts[0]
        const pctStr = Math.abs(c.a) > 0.005 ? ` (${formatPct(c.delta / c.a)})` : ''
        parts.push(
          `${c.cleanName} was reduced by ${formatDollar(Math.abs(c.delta))}${pctStr} — a cut that suggests the district prioritized other areas of the budget over this one.`
        )
      } else {
        const cutNames = topCuts.slice(0, 3).map(c => c.cleanName)
        const lastCut = cutNames.pop()
        parts.push(
          `The proposed budget reduces funding across ${topCuts.length} areas — including ${cutNames.join(', ')}${lastCut ? `, and ${lastCut}` : ''} — for a combined reduction of ${formatDollar(Math.abs(totalCutAmt))}.`
        )
        parts.push(`These reductions suggest the district prioritized direct student services over administrative and discretionary spending.`)
      }
    }
    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 5: School-by-school impacts ────────────────────────────────────
  if (schoolList.length > 0) {
    const parts: string[] = []
    const sorted = [...schoolList].sort((a, b) => b.delta - a.delta)
    const anyDecreased = sorted.some(s => s.delta < -1_000)
    const allUp = sorted.every(s => s.delta >= 0)

    parts.push(
      `Beyond the district-wide numbers, here is what this budget means for families at each school building.`
    )

    for (const s of sorted) {
      const pctStr = s.pctChange !== null ? ` (${fmtPctMag(s.pctChange)})` : ''
      const dir = s.delta >= 0 ? 'up' : 'down'
      const amt = formatDollar(Math.abs(s.delta))

      if (s.key === sorted[0].key && Math.abs(s.delta) > 10_000) {
        // biggest change — most narrative
        parts.push(
          `${s.name} sees the largest shift: spending is ${dir} ${amt}${pctStr}, making it the school most directly affected by this year's budget decisions.`
        )
      } else if (s.delta < -1_000) {
        parts.push(
          `${s.name} families should note a reduction of ${amt}${pctStr} — watch for changes in staffing or program availability at that building.`
        )
      } else if (Math.abs(s.delta) < 3_000) {
        parts.push(
          `${s.name} is essentially flat — an unchanged budget at the building level generally means no new programs, but also no cuts.`
        )
      } else {
        parts.push(
          `${s.name} is ${dir} ${amt}${pctStr}.`
        )
      }
    }

    if (allUp) {
      parts.push(
        `All four schools receive increased budgets this year — a sign that the district is not balancing the books by cutting at the building level.`
      )
    } else if (anyDecreased) {
      parts.push(
        `It is worth noting that not all schools share equally in this budget's resources — families at schools that saw reductions should engage with building-level administrators about how those changes will be managed.`
      )
    }

    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 6: Programs — arts vs. athletics, special education ─────────────
  {
    const parts: string[] = []

    // ── Athletics
    if (athPrimary > 0) {
      const athDir = athDelta >= 0 ? 'up' : 'down'
      const athAmt = formatDollar(Math.abs(athDelta))
      const athPctStr = athPct !== null ? ` (${fmtPctMag(athPct)})` : ''
      if (Math.abs(athDelta) < 1_000) {
        parts.push(
          `For families of student-athletes, the athletics budget is holding essentially flat at ${formatDollar(athPrimary)} — programs and coaching positions are expected to remain stable.`
        )
      } else {
        parts.push(
          `For families of student-athletes, the athletics and activities budget is ${athDir} ${athAmt}${athPctStr} to ${formatDollar(athPrimary)}.`
        )
        if (athDelta > 0) {
          parts.push(`This reflects continued investment in competitive sports, coaching, and after-school activities.`)
        } else {
          parts.push(`Families should watch for potential changes to program offerings, transportation for away events, or coaching staffing.`)
        }
      }
    }

    // ── Arts / Music — always compare directly to athletics
    if (artsPrimary > 0 || artsCompare > 0) {
      const artsDir = artsDelta >= 0 ? 'up' : 'down'
      const artsAmt = formatDollar(Math.abs(artsDelta))
      const artsPctStr = artsPct !== null ? ` (${fmtPctMag(artsPct)})` : ''

      if (Math.abs(artsDelta) < 500 && Math.abs(athDelta) < 1_000) {
        // Both essentially flat
        parts.push(
          `Music, arts, and performing arts programs are also holding steady at ${formatDollar(artsPrimary)} — band, chorus, visual arts, and drama families can expect no major disruptions.`
        )
      } else if (artsDelta < 0 && athDelta >= 0) {
        // Arts cut, athletics held or grew — the most important story to tell
        parts.push(
          `Music, arts, and performing arts programs, however, tell a different story: spending is ${artsDir} ${artsAmt}${artsPctStr} to ${formatDollar(artsPrimary)}.`
        )
        parts.push(
          `Families of students in band, chorus, visual arts, theater, and dance should be aware that while athletics funding is ${athDelta > 0 ? 'growing' : 'holding'}, arts programs are absorbing cuts — a tradeoff that can affect elective availability, instrument access, and production budgets.`
        )
      } else if (artsDelta > 0 && athDelta < 0) {
        // Arts grew, athletics cut — less common but worth noting
        parts.push(
          `In a notable reversal of the typical pattern, music and arts programs are ${artsDir} ${artsAmt}${artsPctStr}, while athletics is being reduced.`
        )
        parts.push(
          `This is good news for families of students in band, chorus, theater, and visual arts.`
        )
      } else {
        // Both moving in same direction
        const bothDir = artsDelta >= 0 ? 'growing' : 'being reduced'
        parts.push(
          `Music, arts, and performing arts programs are ${artsDir} ${artsAmt}${artsPctStr} to ${formatDollar(artsPrimary)} — moving in the same direction as athletics, with both programs ${bothDir} this year.`
        )
        if (artsDelta < 0) {
          parts.push(
            `Families of students in band, chorus, visual arts, and theater should engage with the district to understand how these reductions will be managed without eliminating program options.`
          )
        }
      }
    }

    // ── Special education — always include, always frame around families with IEPs
    if (spedPrimary > 0) {
      const spedDir = spedDelta >= 0 ? 'up' : 'down'
      const spedAmt = formatDollar(Math.abs(spedDelta))
      const spedPctStr = spedPct !== null ? ` (${fmtPctMag(spedPct)})` : ''

      parts.push(
        `For the many Lunenburg families navigating special education — students with IEPs, 504 plans, speech services, occupational therapy, or paraprofessional support — the district's special education budget is ${spedDir} ${spedAmt}${spedPctStr} to ${formatDollar(spedPrimary)}.`
      )
      if (spedDelta > 10_000) {
        parts.push(
          `This increase reflects growing caseloads and rising out-of-district placement costs, not new program investments — but it does signal that the district is meeting its legal obligations under IDEA and state law, regardless of the budget pressure it creates.`
        )
      } else if (spedDelta < -5_000) {
        parts.push(
          `Families receiving special education services should know that any reduction in this budget does not mean a reduction in legally required services — those rights are protected by federal and state law, and the district is obligated to provide them regardless of budget conditions.`
        )
      } else {
        parts.push(
          `Special education services — teachers, paraprofessionals, therapists, and out-of-district placements — remain a legally protected obligation, and this budget continues to fund them fully.`
        )
      }
    }

    if (parts.length > 0) paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 7 (was 5): Where we're investing ──────────────────────────────
  {
    const parts: string[] = []

    if (instrDelta > 0) {
      parts.push(
        `Even within these constraints, the proposed budget directs meaningful spending toward what matters most: the classroom.`
      )
      parts.push(
        `Instructional spending — teachers, curriculum, and direct student programs — totals ${formatDollar(instrPrimary)}, or ${instrShare}% of the overall budget, ${instrDelta > 0 ? `up ${formatDollar(instrDelta)}${instrPct !== null ? ` (${formatPct(instrPct)})` : ''} from last year` : `essentially flat compared to last year`}.`
      )
    } else {
      parts.push(`Instructional spending totals ${formatDollar(instrPrimary)}, representing ${instrShare}% of the overall budget.`)
    }

    // Identify a "double down" investment — the fastest-growing department by % with meaningful dollars
    const doubleDown = [...groupDeltas]
      .filter(g => g.a > 25_000 && g.delta > 0)
      .map(g => ({ ...g, growth: g.delta / g.a }))
      .sort((a, b) => b.growth - a.growth)[0]

    if (doubleDown && doubleDown.growth > 0.08) {
      parts.push(
        `The proposed budget also increases investment in ${doubleDown.cleanName} by ${formatPct(doubleDown.growth)} this year.`,
        `This suggests the district views this area — ${doubleDown.categoryCode ? `part of the ${CATEGORY_LABELS[doubleDown.categoryCode as CategoryCode]} budget` : 'a key program area'} — as a priority for student outcomes.`
      )
    }

    paragraphs.push(parts.join(' '))
  }

  // ── Paragraph 6: Historical context and closing ──────────────────────────────
  {
    const parts: string[] = []

    if (historicalAvg !== null && totalPctChange !== null && yearOverYearChanges.length >= 2) {
      const vsAvg = totalPctChange > historicalAvg
        ? `above the district's ${yearOverYearChanges.length}-year average of ${formatPct(historicalAvg)}`
        : Math.abs(totalPctChange - historicalAvg) < 0.005
        ? `right in line with the district's ${yearOverYearChanges.length}-year average of ${formatPct(historicalAvg)}`
        : `below the district's ${yearOverYearChanges.length}-year average of ${formatPct(historicalAvg)}`

      if (totalPctChange > historicalAvg) {
        parts.push(
          `To put this in context: this year's ${formatPct(totalPctChange)} increase is ${vsAvg} per year, a rate that reflects genuine cost pressures rather than program expansion.`
        )
        parts.push(
          `The district has not absorbed all of these increases internally — particularly in personnel and fixed costs — without requesting additional community support.`
        )
      } else {
        parts.push(
          `This year's ${formatPct(totalPctChange)} change is ${vsAvg}, a sign that the district continues to manage its resources carefully even as costs rise.`
        )
      }
    }

    parts.push(
      `Every dollar in this budget is a public investment — and a public cost — for Lunenburg students and families.`,
      `Understanding where that money goes, and whether it's working, is exactly what this data is here to help you explore.`
    )
    paragraphs.push(parts.join(' '))
  }

  return { paragraphs, primaryLabel, compareLabel }
}

// ── High-level summary cards (hero row + grid) ────────────────────────────────

export interface InsightCard {
  id: string
  title: string
  stat: string
  description: string
  type: InsightType
  href?: string
}

// ── Cost-drivers chart ────────────────────────────────────────────────────────

export interface CostDriverDatum {
  deptName: string    // truncated for chart axis (avoid 'name' — reserved by Recharts)
  fullName: string
  code: string
  delta: number
  pctChange: number | null
}

// ── Category drivers chart ────────────────────────────────────────────────────

export interface CategoryDriverDatum {
  catCode: string
  catLabel: string
  additions: number   // sum of positive group deltas in this category (>= 0)
  reductions: number  // sum of negative group deltas in this category (<= 0)
  net: number
}

export interface CategoryDriversResult {
  rows: CategoryDriverDatum[]
  grossAdded: number      // total $ added across all categories
  grossCut: number        // total $ cut (negative)
  net: number
  addedDeptCount: number  // number of individual department-level increases
  cutDeptCount: number    // number of individual department-level decreases
  expensesDelta: number   // net change in expenses section
  salariesDelta: number   // net change in salaries section
}

export function computeCategoryDriversChart(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): CategoryDriversResult {
  const catMap = new Map<string, { additions: number; reductions: number }>()
  let expensesDelta = 0
  let salariesDelta = 0
  let addedDeptCount = 0
  let cutDeptCount = 0

  for (const group of data.groups) {
    if (!group.categoryCode || group.section === 'summary') continue
    const a = group.totals[compareYear] ?? 0
    const b = group.totals[primaryYear] ?? 0
    const delta = b - a
    if (Math.abs(delta) < 100) continue

    if (!catMap.has(group.categoryCode)) {
      catMap.set(group.categoryCode, { additions: 0, reductions: 0 })
    }
    const entry = catMap.get(group.categoryCode)!
    if (delta > 0) { entry.additions += delta; addedDeptCount++ }
    else { entry.reductions += delta; cutDeptCount++ }

    if (group.section === 'expenses') expensesDelta += delta
    else if (group.section === 'salaries') salariesDelta += delta
  }

  const rows: CategoryDriverDatum[] = [...catMap.entries()]
    .map(([code, { additions, reductions }]) => ({
      catCode: code,
      catLabel: CATEGORY_LABELS[code as CategoryCode] ?? `${code}xxx`,
      additions,
      reductions,
      net: additions + reductions,
    }))
    .filter(d => Math.abs(d.net) > 500)
    .sort((a, b) => b.net - a.net)  // increases at top, decreases at bottom

  const grossAdded = rows.reduce((s, r) => s + r.additions, 0)
  const grossCut = rows.reduce((s, r) => s + r.reductions, 0)

  return {
    rows,
    grossAdded,
    grossCut,
    net: grossAdded + grossCut,
    addedDeptCount,
    cutDeptCount,
    expensesDelta,
    salariesDelta,
  }
}

// ── School breakdown ──────────────────────────────────────────────────────────

export interface SchoolGroupChange {
  code: string
  label: string       // cleaned (school prefix stripped)
  delta: number
  pctChange: number | null
  href: string
}

export interface SchoolBudget {
  id: string          // 'ps' | 'es' | 'ms' | 'hs' | 'district'
  abbrev: string      // 'P.S.' | 'District' etc.
  fullName: string    // 'Primary School' | 'District-Wide' etc.
  totalPrimary: number
  totalCompare: number
  delta: number
  pctChange: number | null
  increases: SchoolGroupChange[]
  decreases: SchoolGroupChange[]
}

export function computeSchoolBreakdown(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): SchoolBudget[] {
  // ── Step 1: derive a school key from a group label ─────────────────────────
  // Handles both abbreviated ("P.S. Principals Office") and full-name
  // ("Middle School Principal Office Salaries") forms found in the spreadsheet.
  function schoolKey(rawLabel: string): string | null {
    const label = rawLabel.replace(/^\d+\s*[-–]\s*/, '').trim()
    // Abbreviated form: "P.S.", "E.S.", "M.S.", "H.S." at start
    const m = label.match(/^([A-Z]\.[A-Z]\.)\s/)
    if (m) return m[1].replace(/\./g, '').toLowerCase()   // "ps" | "es" | "ms" | "hs"
    // Full-word form (used in salary section)
    if (/^Primary\s+School\b/i.test(label))     return 'ps'
    if (/^Elementary\s+School\b/i.test(label))  return 'es'
    if (/^Middle\s+School\b/i.test(label))      return 'ms'
    if (/^High\s+School\b/i.test(label))        return 'hs'
    return null
  }

  // ── Step 2: infer human names from key ────────────────────────────────────
  const KEY_META: Record<string, { abbrev: string; fullName: string }> = {
    ps: { abbrev: 'P.S.', fullName: 'Primary School' },
    es: { abbrev: 'E.S.', fullName: 'Elementary School' },
    ms: { abbrev: 'M.S.', fullName: 'Middle School' },
    hs: { abbrev: 'H.S.', fullName: 'High School' },
  }

  // Strip the school prefix from a description for display within its school card
  function stripPrefix(text: string): string {
    return text
      .replace(/^[A-Z]\.[A-Z]\.\s*/,  '')
      .replace(/^(Primary|Elementary|Middle|High)\s+School\s*/i, '')
      .trim() || text
  }

  // ── Attribution: line-item level ─────────────────────────────────────────
  // Many group headers have no school prefix, but their individual line items
  // do (e.g. "2330 - Paraprofessionals Spec. Ed" contains "P.S. Special Ed
  // Paraprofessionals", "E.S. Special Ed Paraprofessionals", etc.).
  // We therefore check the LINE ITEM description first, then fall back to the
  // parent group label, then to district-wide.
  const groupLabelByCode = new Map(data.groups.map(g => [g.code, g.label]))

  type Bucket = { totalPrimary: number; totalCompare: number; changes: SchoolGroupChange[] }
  const buckets = new Map<string, Bucket>()
  const ensure = (key: string) => {
    if (!buckets.has(key)) buckets.set(key, { totalPrimary: 0, totalCompare: 0, changes: [] })
    return buckets.get(key)!
  }

  for (const item of data.lineItems) {
    if (item.isGroupHeader || item.section === 'summary') continue
    const a = item.values[compareYear] ?? 0
    const b = item.values[primaryYear] ?? 0
    if (a === 0 && b === 0) continue

    const parentLabel = item.parentCode ? (groupLabelByCode.get(item.parentCode) ?? '') : ''
    const key = schoolKey(item.description) ?? schoolKey(parentLabel) ?? 'district'

    const bucket = ensure(key)
    bucket.totalPrimary += b
    bucket.totalCompare += a

    const delta = b - a
    if (Math.abs(delta) >= 200) {
      const displayLabel = key !== 'district' ? stripPrefix(item.description) : item.description
      bucket.changes.push({
        code: item.parentCode ?? '',
        label: displayLabel || item.description,
        delta,
        pctChange: pct(a, b),
        href: item.parentCode ? `/category/${encodeURIComponent(item.parentCode)}` : '/compare',
      })
    }
  }

  // ── Shape output ──────────────────────────────────────────────────────────
  const SORT_ORDER = ['ps', 'es', 'ms', 'hs', 'district']

  return [...buckets.entries()]
    .map(([key, b]) => {
      const meta = KEY_META[key] ?? { abbrev: 'District', fullName: 'District-Wide' }
      return {
        id: key,
        abbrev: meta.abbrev,
        fullName: meta.fullName,
        totalPrimary: b.totalPrimary,
        totalCompare: b.totalCompare,
        delta: b.totalPrimary - b.totalCompare,
        pctChange: pct(b.totalCompare, b.totalPrimary),
        increases: b.changes.filter(c => c.delta > 0).sort((a, b) => b.delta - a.delta).slice(0, 6),
        decreases: b.changes.filter(c => c.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 6),
      }
    })
    .filter(s => s.totalPrimary > 0 || s.totalCompare > 0)
    .sort((a, b) => {
      const ai = SORT_ORDER.indexOf(a.id)
      const bi = SORT_ORDER.indexOf(b.id)
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi)
    })
}

// ── Detailed thematic sections ────────────────────────────────────────────────

export interface InsightItem {
  id: string
  description: string
  parentLabel: string | null
  section: Section
  yearA: number | null
  yearB: number | null
  delta: number
  pctChange: number | null
  href?: string
}

export interface InsightSection {
  id: string
  title: string
  emoji: string
  intro: string
  items: InsightItem[]
  noItemsText: string
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function pct(a: number, b: number): number | null {
  if (Math.abs(a) < 0.005) return null
  return (b - a) / a
}

// Formats a percentage magnitude without a sign — for use in prose where
// the direction is already expressed in words ("up", "down", "increased", etc.)
function fmtPctMag(value: number): string {
  return `${(Math.abs(value) * 100).toFixed(1)}%`
}

function cleanLabel(label: string): string {
  return label.replace(/^\d+\s*[-–]\s*/, '').trim()
}

function truncate(s: string, max = 32): string {
  return s.length > max ? s.slice(0, max - 1) + '…' : s
}

interface ComputedLineItem {
  id: string
  description: string
  section: Section
  parentCode: string | null
  categoryCode: CategoryCode | null
  a: number
  b: number
  delta: number
  pctChange: number | null
}

function matchesAny(description: string, keywords: string[]): boolean {
  const lower = description.toLowerCase()
  return keywords.some(kw => lower.includes(kw))
}

// ── Main exports ──────────────────────────────────────────────────────────────

export function computeCostDriversChart(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
  topN = 14,
): CostDriverDatum[] {
  return data.groups
    .filter(g => g.section !== 'summary')
    .map(g => {
      const a = g.totals[compareYear] ?? 0
      const b = g.totals[primaryYear] ?? 0
      const delta = b - a
      return {
        deptName: truncate(cleanLabel(g.label), 28),
        fullName: cleanLabel(g.label),
        code: g.code,
        delta,
        pctChange: pct(a, b),
      }
    })
    .filter(d => Math.abs(d.delta) > 1_000)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, topN)
}

export function computeInsights(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): InsightCard[] {
  const { groups, lineItems, grandTotals, sections, years } = data

  const totalPrimary    = grandTotals[primaryYear] ?? 0
  const totalCompare    = grandTotals[compareYear] ?? 0
  const freeCashAdjust  = data.freeCash[compareYear] ?? 0
  const adjustedBase    = totalCompare + freeCashAdjust   // actual prior-year levy
  const totalDelta      = totalPrimary - adjustedBase     // levy delta (free-cash-adjusted)
  const totalPctChange  = pct(adjustedBase, totalPrimary) // levy % change

  const primaryLabel = years.find(y => y.key === primaryYear)?.short ?? primaryYear.toUpperCase()
  const compareLabel = years.find(y => y.key === compareYear)?.short ?? compareYear.toUpperCase()

  const groupDeltas = groups.filter(g => g.section !== 'summary').map(g => ({
    ...g,
    a: g.totals[compareYear] ?? 0,
    b: g.totals[primaryYear] ?? 0,
    delta: (g.totals[primaryYear] ?? 0) - (g.totals[compareYear] ?? 0),
  }))

  const lineDeltas: ComputedLineItem[] = lineItems
    .filter(i => !i.isGroupHeader && i.section !== 'summary')
    .map(i => {
      const a = i.values[compareYear] ?? 0
      const b = i.values[primaryYear] ?? 0
      return { id: i.id, description: i.description, section: i.section,
        parentCode: i.parentCode, categoryCode: i.categoryCode,
        a, b, delta: b - a, pctChange: pct(a, b) }
    })

  const catMap = new Map<CategoryCode, { a: number; b: number }>()
  for (const g of groupDeltas) {
    if (!g.categoryCode) continue
    if (!catMap.has(g.categoryCode)) catMap.set(g.categoryCode, { a: 0, b: 0 })
    const c = catMap.get(g.categoryCode)!
    c.a += g.a; c.b += g.b
  }

  const cards: InsightCard[] = []

  // Hero
  {
    const dir = totalDelta >= 0 ? 'an increase' : 'a decrease'
    const pctStr = totalPctChange !== null ? ` (${formatPct(totalPctChange)})` : ''
    const baseNote = freeCashAdjust < 0
      ? ` ${compareLabel}'s actual levy was ${formatDollar(adjustedBase)} after a ${formatDollar(Math.abs(freeCashAdjust))} one-time free cash offset.`
      : ''
    cards.push({
      id: 'hero', title: 'The Big Picture', stat: formatDollar(totalPrimary), type: totalDelta >= 0 ? 'increase' : 'decrease',
      description: `The ${primaryLabel} proposed budget is ${formatDollar(totalPrimary)} — ${dir} of ${formatDollar(Math.abs(totalDelta))}${pctStr} over ${compareLabel}'s levy of ${formatDollar(adjustedBase)}.${baseNote}`,
    })
  }

  // Biggest new investment
  {
    const top = [...groupDeltas].filter(g => g.delta > 0).sort((a, b) => b.delta - a.delta)[0]
    if (top) {
      const pctStr = Math.abs(top.a) > 0.005 ? ` (${formatPct(top.delta / top.a)})` : ' (new)'
      const catDesc = top.categoryCode ? CATEGORY_DESCRIPTIONS[top.categoryCode] : ''
      cards.push({
        id: 'top-increase', title: 'Biggest New Investment', stat: `+${formatDollar(top.delta)}`, type: 'increase',
        href: `/category/${encodeURIComponent(top.code)}`,
        description: `${cleanLabel(top.label)} is the largest single increase — up from ${formatDollar(top.a)} to ${formatDollar(top.b)}${pctStr}.${catDesc ? ` Covers: ${catDesc}` : ''}`,
      })
    }
  }

  // What was cut
  {
    const cuts = [...groupDeltas].filter(g => g.delta < -5_000).sort((a, b) => a.delta - b.delta)
    if (cuts.length === 0) {
      cards.push({ id: 'cuts', title: 'What Was Cut', stat: 'No reductions', type: 'neutral',
        description: `No department areas were meaningfully reduced from ${compareLabel} to ${primaryLabel}. Every category held steady or increased.` })
    } else {
      const totalCut = cuts.reduce((s, c) => s + c.delta, 0)
      const top = cuts[0]
      const pctStr = Math.abs(top.a) > 0.005 ? ` (${formatPct(top.delta / top.a)})` : ''
      const others = cuts.slice(1, 3).map(c => cleanLabel(c.label)).join(', ')
      cards.push({
        id: 'cuts', title: 'What Was Cut', type: 'decrease',
        href: cuts.length === 1 ? `/category/${encodeURIComponent(top.code)}` : undefined,
        stat: `${formatDollar(Math.abs(totalCut))} across ${cuts.length} area${cuts.length !== 1 ? 's' : ''}`,
        description: `Largest cut: ${cleanLabel(top.label)}, down ${formatDollar(Math.abs(top.delta))}${pctStr} (from ${formatDollar(top.a)} to ${formatDollar(top.b)}).${others ? ` Also reduced: ${others}.` : ''}`,
      })
    }
  }

  // Sharpest % spike in a line item
  {
    const spike = [...lineDeltas].filter(i => i.a > 5_000 && i.delta > 10_000)
      .map(i => ({ ...i, pct2: i.delta / i.a })).sort((a, b) => b.pct2 - a.pct2)[0]
    if (spike && spike.pct2 > 0.5) {
      const parent = groups.find(g => g.code === spike.parentCode)
      cards.push({
        id: 'spike', title: 'Sharpest Cost Spike', type: 'increase',
        href: spike.parentCode ? `/category/${encodeURIComponent(spike.parentCode)}` : undefined,
        stat: truncate(spike.description),
        description: `"${spike.description}" jumped ${formatPct(spike.pct2)} — from ${formatDollar(spike.a)} to ${formatDollar(spike.b)} (+${formatDollar(spike.delta)}).${parent ? ` Part of ${cleanLabel(parent.label)}.` : ''}`,
      })
    }
  }

  // Fastest-growing department
  {
    const fastest = [...groupDeltas].filter(g => g.a > 25_000 && g.delta > 0)
      .map(g => ({ ...g, pctChange: g.delta / g.a })).sort((a, b) => b.pctChange - a.pctChange)[0]
    if (fastest) {
      const catLabel = fastest.categoryCode ? ` (${CATEGORY_LABELS[fastest.categoryCode]})` : ''
      cards.push({
        id: 'fastest', title: 'Fastest Growing Department', type: 'increase',
        href: `/category/${encodeURIComponent(fastest.code)}`,
        stat: cleanLabel(fastest.label),
        description: `${cleanLabel(fastest.label)}${catLabel} grew ${formatPct(fastest.pctChange)} — from ${formatDollar(fastest.a)} to ${formatDollar(fastest.b)} (+${formatDollar(fastest.delta)}).`,
      })
    }
  }

  // Largest category shift
  {
    const topCat = [...catMap.entries()]
      .map(([code, v]) => ({ code, ...v, delta: v.b - v.a, pctChange: pct(v.a, v.b), label: CATEGORY_LABELS[code] }))
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0]
    if (topCat) {
      const pctStr = topCat.pctChange !== null ? ` (${formatPct(topCat.pctChange)})` : ''
      const desc = CATEGORY_DESCRIPTIONS[topCat.code as CategoryCode] ?? ''
      cards.push({
        id: 'category-mover', title: 'Largest Category Shift', type: topCat.delta >= 0 ? 'increase' : 'decrease',
        stat: topCat.label,
        description: `${topCat.label} ${topCat.delta >= 0 ? 'grew' : 'shrank'} the most — ${topCat.delta >= 0 ? '+' : ''}${formatDollar(topCat.delta)}${pctStr}, from ${formatDollar(topCat.a)} to ${formatDollar(topCat.b)}.${desc ? ` Covers: ${desc}` : ''}`,
      })
    }
  }

  // Staff & salaries
  {
    const sal = (yr: FiscalYear) => sections.salaries.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[yr] ?? 0), 0)
    const salP = sal(primaryYear), salC = sal(compareYear)
    const salD = salP - salC
    const centsNow = totalPrimary > 0 ? Math.round((salP / totalPrimary) * 100) : 0
    const centsThen = totalCompare > 0 ? Math.round((salC / totalCompare) * 100) : 0
    const centsDir = centsNow === centsThen ? `unchanged from ${compareLabel}` : `${centsNow > centsThen ? 'up' : 'down'} from ${centsThen}¢ last year`
    cards.push({
      id: 'salaries', title: 'Staff & Salaries', type: salD >= 0 ? 'increase' : 'decrease',
      stat: `${centsNow}¢ of every dollar`,
      description: `${centsNow}¢ of every budget dollar goes to staff — ${centsDir}. Total compensation: ${formatDollar(salP)}, ${salD >= 0 ? 'up' : 'down'} ${formatDollar(Math.abs(salD))}${pct(salC, salP) !== null ? ` (${formatPct(pct(salC, salP))})` : ''} vs. ${compareLabel}.`,
    })
  }

  // Historical context
  {
    if (years.length >= 3 && totalPctChange !== null) {
      const nonProj = years.filter(y => !y.isProjected)
      const changes: number[] = []
      for (let i = 1; i < nonProj.length; i++) {
        const p2 = pct(grandTotals[nonProj[i - 1].key] ?? 0, grandTotals[nonProj[i].key] ?? 0)
        if (p2 !== null) changes.push(p2)
      }
      if (changes.length >= 2) {
        const avg = changes.reduce((s, c) => s + c, 0) / changes.length
        cards.push({
          id: 'context', title: 'Historical Context', type: totalPctChange > avg ? 'increase' : 'decrease',
          stat: `${formatPct(avg)} avg/year`,
          description: `This year's ${formatPct(totalPctChange)} increase is ${totalPctChange > avg ? 'above' : 'below'} the ${changes.length}-year average of ${formatPct(avg)}. Growth has averaged ${formatPct(avg)}/yr since ${nonProj[0].short}.`,
        })
      }
    }
  }

  return cards
}

// ── Detailed thematic sections ────────────────────────────────────────────────

export function computeInsightSections(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): InsightSection[] {
  const { lineItems, groups, sections } = data
  const primaryLabel = data.years.find(y => y.key === primaryYear)?.short ?? primaryYear.toUpperCase()
  // Build a lookup: groupCode → cleanLabel
  const groupLabel = new Map(groups.map(g => [g.code, cleanLabel(g.label)]))

  // Compute all line item deltas
  const allItems: ComputedLineItem[] = lineItems
    .filter(i => !i.isGroupHeader && i.section !== 'summary')
    .map(i => {
      const a = i.values[compareYear] ?? 0
      const b = i.values[primaryYear] ?? 0
      return { id: i.id, description: i.description, section: i.section,
        parentCode: i.parentCode, categoryCode: i.categoryCode,
        a, b, delta: b - a, pctChange: pct(a, b) }
    })

  function toInsightItems(items: ComputedLineItem[]): InsightItem[] {
    return items.map(i => ({
      id: i.id,
      description: i.description,
      parentLabel: i.parentCode ? (groupLabel.get(i.parentCode) ?? null) : null,
      section: i.section,
      yearA: i.a === 0 && i.b === 0 ? null : i.a,
      yearB: i.b === 0 ? null : i.b,
      delta: i.delta,
      pctChange: i.pctChange,
      href: i.parentCode ? `/category/${encodeURIComponent(i.parentCode)}` : undefined,
    }))
  }

  function find(keywords: string[], minAbsDelta = 100): ComputedLineItem[] {
    return allItems
      .filter(i => Math.abs(i.delta) >= minAbsDelta && matchesAny(i.description, keywords))
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
  }

  const result: InsightSection[] = []

  // ── Salaries ────────────────────────────────────────────────────────────────
  {
    // Use group-level salary section data for richer breakdowns
    const salGroups = groups
      .filter(g => g.section === 'salaries')
      .map(g => {
        const a = g.totals[compareYear] ?? 0
        const b = g.totals[primaryYear] ?? 0
        const delta = b - a
        return { id: `sal-${g.code}`, description: cleanLabel(g.label), section: 'salaries' as Section,
          parentLabel: null, yearA: a, yearB: b, delta, pctChange: pct(a, b),
          href: `/category/${encodeURIComponent(g.code)}` }
      })
      .filter(g => Math.abs(g.delta) > 500)
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))

    const salPrimary = sections.salaries.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
    const salCompare = sections.salaries.filter(i => !i.isGroupHeader).reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
    const salDelta = salPrimary - salCompare
    const salPctStr = pct(salCompare, salPrimary) !== null ? ` (${formatPct(pct(salCompare, salPrimary))})` : ''

    result.push({
      id: 'salaries',
      title: 'Salaries & Compensation',
      emoji: '🧑‍🏫',
      intro: `Total salaries are ${salDelta >= 0 ? 'up' : 'down'} ${formatDollar(Math.abs(salDelta))}${salPctStr} — from ${formatDollar(salCompare)} to ${formatDollar(salPrimary)}. Here's how each department's compensation changed:`,
      items: salGroups,
      noItemsText: 'No salary data found.',
    })
  }

  // ── Music, Arts & Performing Arts ──────────────────────────────────────────
  {
    const items = find(['music', 'band', 'chorus', 'orchestra', 'choir', 'art ', 'arts ', ' art', 'drama', 'theater', 'theatre', 'dance', 'performing'])
    result.push({
      id: 'arts',
      title: 'Music, Arts & Performing Arts',
      emoji: '🎵',
      intro: `These line items cover music programs, visual arts, drama, and performing arts. Changes here directly affect what artistic opportunities are available to students.`,
      items: toInsightItems(items),
      noItemsText: `No music or arts line items found in the ${primaryLabel} budget.`,
    })
  }

  // ── Athletics & Physical Education ─────────────────────────────────────────
  {
    const items = find(['athletic', 'athletics', 'physical education', 'coaching', ' coach', 'interscholastic', 'sports', 'extracurricular', 'after school', 'after-school', 'fitness'])
    result.push({
      id: 'athletics',
      title: 'Athletics & Physical Education',
      emoji: '🏃',
      intro: `Covers PE classes, team sports, coaches, and after-school athletic programs.`,
      items: toInsightItems(items),
      noItemsText: `No athletics or PE line items with notable changes found.`,
    })
  }

  // ── Special Education & Student Support ────────────────────────────────────
  {
    const items = find(['special ed', 'special education', 'sped', 'inclusion', 'paraprofessional', 'para ', 'occupational', 'physical therapy', 'speech', 'language', 'counseling', 'counselor', 'psychologist', 'social worker', 'nurse', 'nursing', 'guidance', 'tutoring'])
    result.push({
      id: 'sped',
      title: 'Special Education & Student Support',
      emoji: '🎓',
      intro: `Includes special education teachers, aides, therapists, counselors, and nurses. This is one of the most federally-mandated and legally required parts of the budget.`,
      items: toInsightItems(items),
      noItemsText: `No special education or student support line items with notable changes found.`,
    })
  }

  // ── Transportation ─────────────────────────────────────────────────────────
  {
    const items = find(['transport', 'bus ', 'busing', 'vehicle', 'driver', 'routing'])
    result.push({
      id: 'transportation',
      title: 'Transportation',
      emoji: '🚌',
      intro: `Student transportation costs, including regular routes and specialized transportation for students with disabilities.`,
      items: toInsightItems(items),
      noItemsText: `No transportation line items with notable changes found.`,
    })
  }

  // ── Technology ─────────────────────────────────────────────────────────────
  {
    const items = find(['technology', 'tech ', 'computer', 'software', 'hardware', 'network', 'chromebook', 'laptop', 'device', 'subscription', 'license', 'digital', 'internet', 'wifi', 'infrastructure'])
    result.push({
      id: 'technology',
      title: 'Technology & Infrastructure',
      emoji: '💻',
      intro: `Devices, software licenses, network infrastructure, and educational technology platforms used by students and staff.`,
      items: toInsightItems(items),
      noItemsText: `No technology line items with notable changes found.`,
    })
  }

  // ── Supplies, Materials & Textbooks ────────────────────────────────────────
  {
    const items = find(['supplies', 'textbook', 'material', ' books', 'workbook', 'curriculum materials', 'instructional materials', 'office supplies', 'paper', 'printing', 'copies'])
    result.push({
      id: 'supplies',
      title: 'Supplies, Materials & Textbooks',
      emoji: '📚',
      intro: `Classroom supplies, textbooks, workbooks, and instructional materials. Declines here can mean teachers pay out of pocket or go without.`,
      items: toInsightItems(items),
      noItemsText: `No supplies or materials line items with notable changes found.`,
    })
  }

  // ── Facilities & Operations ─────────────────────────────────────────────────
  {
    const items = find(['custodial', 'custodian', 'maintenance', 'grounds', 'utilities', 'electric', 'heat', 'gas ', 'energy', 'security', 'cleaning', 'janitorial', 'renovation', 'repair'])
    result.push({
      id: 'facilities',
      title: 'Facilities & Operations',
      emoji: '🏫',
      intro: `Building maintenance, utilities, custodial services, and grounds upkeep. These costs are largely non-discretionary.`,
      items: toInsightItems(items),
      noItemsText: `No facilities or operations line items with notable changes found.`,
    })
  }

  // ── Administration ──────────────────────────────────────────────────────────
  {
    const adminGroups = groups
      .filter(g => g.categoryCode === '1')
      .map(g => {
        const a = g.totals[compareYear] ?? 0
        const b = g.totals[primaryYear] ?? 0
        const delta = b - a
        return { id: `admin-${g.code}`, description: cleanLabel(g.label), section: g.section,
          parentLabel: null, yearA: a, yearB: b, delta, pctChange: pct(a, b),
          href: `/category/${encodeURIComponent(g.code)}` }
      })
      .filter(g => Math.abs(g.delta) > 500)
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))

    result.push({
      id: 'admin',
      title: 'Administration & Central Office',
      emoji: '🏛️',
      intro: `Costs for district leadership, HR, legal, finance, and technology administration. The public often scrutinizes this category to see whether classroom dollars are being protected.`,
      items: adminGroups,
      noItemsText: `No administration line items with notable changes found.`,
    })
  }

  // ── Fixed Costs (Insurance, Benefits) ──────────────────────────────────────
  {
    const items = find(['insurance', 'benefit', 'retirement', 'pension', 'fica', 'medicare', 'workers comp', 'unemployment', 'health insurance', 'dental', 'vision'])
    result.push({
      id: 'fixed-costs',
      title: 'Fixed Costs: Benefits & Insurance',
      emoji: '🛡️',
      intro: `Health insurance, retirement contributions, and other employee benefits. These costs are largely outside district control and tend to rise faster than inflation.`,
      items: toInsightItems(items),
      noItemsText: `No benefits or insurance line items with notable changes found.`,
    })
  }

  // Filter out sections with no items
  return result.filter(s => s.items.length > 0)
}

// ── Prop 2½ context ───────────────────────────────────────────────────────────
//
// Compares the school budget year-over-year change against the 2.5% annual
// levy cap. This is NOT a definitive override determination — that requires
// the full town levy picture — but it surfaces whether the school budget
// alone is above or below the cap threshold.

export interface Prop25Metrics {
  budgetPctChange: number | null   // gross line-item YoY % change
  levyPctChange: number | null     // actual levy % change (free-cash-adjusted)
  capPct: number                   // always 0.025
  isAboveCap: boolean
  pptAboveCap: number | null       // ppts above cap (levy basis; negative = under cap)
  dollarAboveCap: number           // $ above what 2.5% would allow (levy basis)
  capAmount: number                // what 2.5% growth on the adjusted levy base equals
  totalDelta: number               // gross line-item delta
  levyDelta: number                // actual levy delta (totalPrimary - adjustedBase)
  totalPrimary: number             // budget used for Prop 2½ (town manager override if present)
  requestedTotal: number           // school's own spreadsheet grand total
  townManagerTotal: number | null  // non-null when supplemental.csv provided an override
  totalCompare: number             // gross compare-year total
  adjustedBase: number             // compare-year levy after free cash (Prop 2½ base)
  freeCashAdjust: number           // free cash used in compare year (≤ 0)
}

// Find a supplemental value whose label contains the given year short name and all
// required keywords, and none of the excluded keywords (all case-insensitive).
function findSupplemental(
  supplemental: Array<{ label: string; value: number }>,
  yearShort: string,
  include: string[],
  exclude: string[] = [],
): number | null {
  const entry = supplemental.find(s => {
    const l = s.label.toLowerCase()
    return (
      l.includes(yearShort.toLowerCase()) &&
      include.every(k => l.includes(k.toLowerCase())) &&
      exclude.every(k => !l.includes(k.toLowerCase()))
    )
  })
  return entry?.value ?? null
}

export function computeProp25(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): Prop25Metrics {
  const requestedTotal  = data.grandTotals[primaryYear] ?? 0
  const totalCompare    = data.grandTotals[compareYear] ?? 0
  const freeCashAdjust  = data.freeCash[compareYear] ?? 0   // negative value or 0
  // The actual levy base is the gross total minus the one-time free cash offset
  const adjustedBase    = totalCompare + freeCashAdjust     // e.g. 26,287,474 + (-500,000)

  // Use the town manager's approved budget from supplemental.csv when available;
  // otherwise fall back to the school's own spreadsheet grand total.
  const yearShort        = data.years.find(y => y.key === primaryYear)?.short ?? ''
  const townManagerTotal = findSupplemental(data.supplemental, yearShort, ['budget'], ['increase'])
  const totalPrimary     = townManagerTotal ?? requestedTotal

  const totalDelta      = totalPrimary - totalCompare
  const levyDelta       = totalPrimary - adjustedBase
  const budgetPctChange = totalCompare > 0.005 ? totalDelta / totalCompare : null
  const levyPctChange   = adjustedBase > 0.005 ? levyDelta / adjustedBase : null
  // Prop 2½ cap is measured on the actual levy (adjustedBase), not the gross line-item total
  const capAmount       = adjustedBase * 0.025
  const dollarAboveCap  = levyDelta - capAmount
  const pptAboveCap     = levyPctChange !== null ? levyPctChange - 0.025 : null
  const isAboveCap      = pptAboveCap !== null && pptAboveCap > 0

  return {
    budgetPctChange,
    levyPctChange,
    capPct: 0.025,
    isAboveCap,
    pptAboveCap,
    dollarAboveCap,
    capAmount,
    totalDelta,
    levyDelta,
    totalPrimary,
    requestedTotal,
    townManagerTotal,
    totalCompare,
    adjustedBase,
    freeCashAdjust,
  }
}

// ── Public review: anomaly detection ──────────────────────────────────────────
//
// Flags individual line items that fall outside normal year-over-year patterns:
//   • new        — line item did not exist (or was negligible) in compareYear
//   • eliminated — line item existed in compareYear but is gone (or negligible) now
//   • spike      — grew > 50% AND added > $15k (well above a typical 3-6% budget trend)
//   • sharp-cut  — fell > 40% AND cut > $10k

export type AnomalyType = 'new' | 'eliminated' | 'spike' | 'sharp-cut'

export interface Anomaly {
  id: string
  type: AnomalyType
  severity: 'high' | 'medium'   // high = dollar impact is large
  description: string
  parentLabel: string
  parentCode: string | null
  section: 'expenses' | 'salaries'
  compareValue: number | null    // null = truly absent in prior year
  primaryValue: number | null    // null = truly absent in current year
  delta: number
  pctChange: number | null
  href: string
}

export function computeAnomalies(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): Anomaly[] {
  const { lineItems, groups } = data
  const glMap = new Map(groups.map(g => [g.code, g.label]))

  const results: Anomaly[] = []

  for (const item of lineItems) {
    if (item.isGroupHeader || item.section === 'summary') continue

    const rawA = item.values[compareYear]
    const rawB = item.values[primaryYear]
    const a = rawA ?? 0
    const b = rawB ?? 0
    const delta = b - a
    const pctChange = Math.abs(a) > 0.005 ? delta / a : null

    const rawParent = item.parentCode ? (glMap.get(item.parentCode) ?? '') : ''
    const parentLabel = rawParent.replace(/^\d+\s*[-–]\s*/, '').trim()
    const href = item.parentCode
      ? `/category/${encodeURIComponent(item.parentCode)}`
      : '/overview'
    const section = item.section as 'expenses' | 'salaries'

    // ── New spending: appeared this year (was absent or tiny before)
    if ((rawA == null || a < 200) && b > 5_000) {
      results.push({
        id: item.id, type: 'new',
        severity: b > 50_000 ? 'high' : 'medium',
        description: item.description,
        parentLabel, parentCode: item.parentCode,
        section, href,
        compareValue: rawA == null ? null : a,
        primaryValue: b,
        delta, pctChange: null,
      })
      continue
    }

    // ── Eliminated: was funded, now gone (absent or tiny now)
    if (a > 5_000 && (rawB == null || b < 200)) {
      results.push({
        id: item.id, type: 'eliminated',
        severity: a > 50_000 ? 'high' : 'medium',
        description: item.description,
        parentLabel, parentCode: item.parentCode,
        section, href,
        compareValue: a,
        primaryValue: rawB == null ? null : b,
        delta, pctChange: null,
      })
      continue
    }

    // ── Spike: grew > 50% with meaningful new dollars
    if (pctChange !== null && pctChange > 0.5 && delta > 15_000) {
      results.push({
        id: item.id, type: 'spike',
        severity: delta > 60_000 || pctChange > 1.5 ? 'high' : 'medium',
        description: item.description,
        parentLabel, parentCode: item.parentCode,
        section, href,
        compareValue: a, primaryValue: b,
        delta, pctChange,
      })
      continue
    }

    // ── Sharp cut: fell > 40% with meaningful dollar reduction
    if (pctChange !== null && pctChange < -0.4 && Math.abs(delta) > 10_000) {
      results.push({
        id: item.id, type: 'sharp-cut',
        severity: Math.abs(delta) > 50_000 || pctChange < -0.7 ? 'high' : 'medium',
        description: item.description,
        parentLabel, parentCode: item.parentCode,
        section, href,
        compareValue: a, primaryValue: b,
        delta, pctChange,
      })
    }
  }

  // Sort: high severity first, then by absolute dollar amount
  return results
    .sort((a, b) => {
      if (a.severity !== b.severity) return a.severity === 'high' ? -1 : 1
      return Math.abs(b.delta) - Math.abs(a.delta)
    })
    .slice(0, 30)
}
