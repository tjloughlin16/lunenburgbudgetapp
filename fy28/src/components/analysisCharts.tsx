import type { ReactNode } from 'react'
import {
  TownPersonnelShare, TownPersonnelCounts, TownPersonnelAll,
  TownPersonnelFire, TownPersonnelCrowd, TownPersonnelPeople,
} from './TownPersonnelCharts'
import { BoardCompositionWhere, BoardCompositionFill } from './BoardCompositionCharts'
import {
  StabilizationAll, StabilizationEach, StabilizationGrowth, StabilizationFlows,
  StabilizationHoldings,
} from './StabilizationCharts'
import {
  StabilizationOptionSplit, StabilizationOptionBurndown,
} from './StabilizationOptionCharts'
import {
  TownBudgetsShare, TownBudgetsAll, TownBudgetsRates, TownBudgetsPull,
  TownBudgetsTrends, TownBudgetsTotal, TownBudgetsTown,
} from './TownBudgetsCharts'

/* THE REGISTRY THAT LETS A CHART STOP BEING A PICTURE.
 *
 * TJ, 22 September 2026: *"we shouldnt ever just embed charts as images. thats a bad
 * model. we need to update them all to actual charts."* Rule 7f.
 *
 * `renderMarkdown` meets `![alt](charts/foo.svg)` in an analysis and asks here whether a
 * component is registered under `foo`. If one is, it is rendered in the figure's place
 * and the caption is kept; if not, the <img> renders exactly as before.
 *
 * THAT FALLBACK IS THE POINT. Twenty-five chart images exist across eight analyses, and a
 * conversion that had to be finished in one pass would either not start or would land
 * half-done with some analyses silently missing their charts. This way each one converts
 * on its own, an unconverted chart still appears, and a NEW chart that nobody has written
 * a component for yet is never invisible.
 *
 * Every component here reads the report's own payload -- the same /data/<id>.json that
 * feeds the stat row -- so there is one set of figures, not one for the page and one for
 * the picture. Nothing in this folder computes a figure (rule 2). */

export type ChartProps = { data: unknown; alt: string }

export const ANALYSIS_CHARTS: Record<string, (p: ChartProps) => ReactNode> = {
  'town-personnel-crowd': TownPersonnelCrowd,
  'town-personnel-share': TownPersonnelShare,
  'town-personnel-counts': TownPersonnelCounts,
  'town-personnel-all': TownPersonnelAll,
  'town-personnel-people': TownPersonnelPeople,
  'town-personnel-fire': TownPersonnelFire,
  'town-budgets-town': TownBudgetsTown,
  'town-budgets-share': TownBudgetsShare,
  'town-budgets-all': TownBudgetsAll,
  'town-budgets-rates': TownBudgetsRates,
  'town-budgets-pull': TownBudgetsPull,
  'town-budgets-trends': TownBudgetsTrends,
  'town-budgets-total': TownBudgetsTotal,
  'board-composition-where': BoardCompositionWhere,
  'board-composition-fill': BoardCompositionFill,
  'stabilization-all': StabilizationAll,
  'stabilization-each': StabilizationEach,
  'stabilization-growth': StabilizationGrowth,
  'stabilization-flows': StabilizationFlows,
  'stabilization-holdings': StabilizationHoldings,
  'stabilization-option-split': StabilizationOptionSplit,
  'stabilization-option-burndown': StabilizationOptionBurndown,
}

/** The chart registered for `charts/foo.svg`, or undefined to fall back to the image. */
export function chartFor(src: string) {
  const m = /([a-z0-9-]+)\.svg$/i.exec(src)
  return m ? ANALYSIS_CHARTS[m[1]] : undefined
}
