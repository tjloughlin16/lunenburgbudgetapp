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

/* A CHART MUST SAY WHAT IT NEEDS, and the build caught why.
 *
 * `town-budget-protection` embeds `town-personnel-fire.svg` -- the same picture, on a
 * different report -- and this registry matched it by CHART NAME and handed the component
 * that page's own payload, which has no `fire` in it. The component read `.fire.map` on
 * undefined, threw, and the whole page prerendered as ZERO characters. One chart shared
 * between two reports took the report down.
 *
 * So every entry declares what it needs from the payload, and a chart whose data is not
 * there falls back to the image exactly as an unconverted chart does. That is the same
 * rule as the fallback itself: a chart that cannot be drawn must be a picture, never an
 * empty page. And it is the repo's own lesson about joins -- something that matches
 * nothing has to say so rather than quietly producing nothing. */
type Entry = {
  render: (p: ChartProps) => ReactNode
  needs: (d: Record<string, unknown>) => boolean
}

const has = (...keys: string[]) => (d: Record<string, unknown>) =>
  keys.every(k => d?.[k] != null)

export const ANALYSIS_CHARTS: Record<string, Entry> = {
  'town-personnel-crowd': { render: TownPersonnelCrowd, needs: has('employers','pictogram') },
  'town-personnel-share': { render: TownPersonnelShare, needs: has('employers') },
  'town-personnel-counts': { render: TownPersonnelCounts, needs: has('employers') },
  'town-personnel-all': { render: TownPersonnelAll, needs: has('employers') },
  'town-personnel-people': { render: TownPersonnelPeople, needs: has('employers','pictogram') },
  'town-personnel-fire': { render: TownPersonnelFire, needs: has('fire') },
  'town-budgets-town': { render: TownBudgetsTown, needs: has('departments','pictogram') },
  'town-budgets-share': { render: TownBudgetsShare, needs: has('departments') },
  'town-budgets-all': { render: TownBudgetsAll, needs: has('departments','detail_years') },
  'town-budgets-rates': { render: TownBudgetsRates, needs: has('departments','levy_cap') },
  'town-budgets-pull': { render: TownBudgetsPull, needs: has('departments') },
  'town-budgets-trends': { render: TownBudgetsTrends, needs: has('departments','detail_years','levy_cap') },
  'town-budgets-total': { render: TownBudgetsTotal, needs: has('totals') },
  'board-composition-where': { render: BoardCompositionWhere, needs: has('sizes') },
  'board-composition-fill': { render: BoardCompositionFill, needs: has('fill') },
  'stabilization-all': { render: StabilizationAll, needs: has('series') },
  'stabilization-each': { render: StabilizationEach, needs: has('series') },
  'stabilization-growth': { render: StabilizationGrowth, needs: has('series') },
  'stabilization-flows': { render: StabilizationFlows, needs: has('flows') },
  'stabilization-holdings': { render: StabilizationHoldings, needs: has('funds','totals') },
  'stabilization-option-split': { render: StabilizationOptionSplit, needs: has('both') },
  'stabilization-option-burndown': { render: StabilizationOptionBurndown, needs: has('burndown') },
}

/** The chart registered for `charts/foo.svg` IF this payload can feed it, else undefined
 *  so the caller renders the image. */
export function chartFor(src: string, data: unknown) {
  const m = /([a-z0-9-]+)\.svg$/i.exec(src)
  const e = m ? ANALYSIS_CHARTS[m[1]] : undefined
  if (!e) return undefined
  return e.needs((data ?? {}) as Record<string, unknown>) ? e.render : undefined
}
