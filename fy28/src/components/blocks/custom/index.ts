/** ONE-OFF DIAGRAMS, one per page that needed a picture nothing else draws.
 *
 *  TJ, 25 October 2026: "you can build diagrams, charts, or whatever on the fly even if we
 *  dont have templates for them or havent used them before ... for ANY page, hub we build."
 *
 *  To add one: write <id>.tsx in this folder, a component taking { data, alt }; register it
 *  below; emit it from the page's generator with topic_blocks.custom('<id>', title, data,
 *  figures=..., allow=...). The generator checks every string in `data` against rule 2; the
 *  component formats nothing and draws from the payload (rule 7f). When one is used on a
 *  second page, promote it to a named block in Blocks.tsx and scripts/topic_blocks.py. */
import type { ComponentType } from 'react'
import BvaAcross from './bva-across'
import BvaGrid from './bva-grid'
import CapitalLadder from './capital-ladder'
import CapitalPath from './capital-path'
import CapitalThreadTable from './capital-thread-table'
import CapitalShareBands from './capital-share-bands'
import CapitalTwoOrders from './capital-two-orders'
import CapitalUnrankedList from './capital-unranked-list'
import CapitalCoverage from './capital-coverage'
import CapitalDeptYears from './capital-dept-years'
import CapitalRequestSizes from './capital-request-sizes'
import DollarStrips from './dollar-strips'
import FyFlags from './fy-flags'
import FyLineTable from './fy-line-table'
import FyYearFacts from './fy-year-facts'
import FyYearPicker from './fy-year-picker'
import FyOverlap from './fy-overlap'
import FyYearLine from './fy-year-line'
import FyReadiness from './fy-readiness'
import FyBridge from './fy-bridge'
import FyLineFunds from './fy-line-funds'
import FyBudgetChanges from './fy-budget-changes'
import FyFundMoves from './fy-fund-moves'
import FyPayees from './fy-payees'
import FyPlan from './fy-plan'
import FyFundFlows from './fy-fund-flows'
import FyBigChanges from './fy-big-changes'
import FySources from './fy-sources'
import FySalaries from './fy-salaries'
import FyWeb from './fy-web'
import FySourceTable from './fy-source-table'
import FyYearWeeks from './fy-year-weeks'
import FyTownReceipts from './fy-town-receipts'
import FySignatures from './fy-signatures'
import GrantAwardsStack from './grant-awards-stack'
import MeetingTrail from './meeting-trail'
import SerfMoneyStack from './serf-money-stack'
import SerfSaidLedger from './serf-said-ledger'
import HomesAgainstInflation from './homes-against-inflation'
import ParkFundMonths from './park-fund-months'
import ParkSalesMonths from './park-sales-months'
import SchoolDraftLines from './school-draft-lines'
import EntryTrail from './entry-trail'
import TalkingPoints from './talking-points'
import BigFigures from './big-figures'
import OodWhoPaid from './ood-who-paid'
import OodComposition from './ood-composition'

export type CustomProps = { data: unknown; alt: string }

export const CUSTOM_BLOCKS: Record<string, ComponentType<CustomProps>> = {
  'bva-across': BvaAcross,
  'bva-grid': BvaGrid,
  'capital-ladder': CapitalLadder,
  'capital-path': CapitalPath,
  'capital-thread-table': CapitalThreadTable,
  'capital-share-bands': CapitalShareBands,
  'capital-two-orders': CapitalTwoOrders,
  'capital-unranked-list': CapitalUnrankedList,
  'capital-coverage': CapitalCoverage,
  'capital-dept-years': CapitalDeptYears,
  'capital-request-sizes': CapitalRequestSizes,
  'dollar-strips': DollarStrips,
  'fy-flags': FyFlags,
  'fy-line-table': FyLineTable,
  'fy-year-facts': FyYearFacts,
  'fy-year-picker': FyYearPicker,
  'fy-overlap': FyOverlap,
  'fy-year-line': FyYearLine,
  'fy-readiness': FyReadiness,
  'fy-bridge': FyBridge,
  'fy-line-funds': FyLineFunds,
  'fy-budget-changes': FyBudgetChanges,
  'fy-fund-moves': FyFundMoves,
  'fy-payees': FyPayees,
  'fy-plan': FyPlan,
  'fy-fund-flows': FyFundFlows,
  'fy-big-changes': FyBigChanges,
  'fy-sources': FySources,
  'fy-salaries': FySalaries,
  'fy-web': FyWeb,
  'fy-source-table': FySourceTable,
  'fy-year-weeks': FyYearWeeks,
  'fy-town-receipts': FyTownReceipts,
  'fy-signatures': FySignatures,
  'grant-awards-stack': GrantAwardsStack,
  'meeting-trail': MeetingTrail,
  'serf-money-stack': SerfMoneyStack,
  'serf-said-ledger': SerfSaidLedger,
  'homes-against-inflation': HomesAgainstInflation,
  'park-fund-months': ParkFundMonths,
  'park-sales-months': ParkSalesMonths,
  'school-draft-lines': SchoolDraftLines,
  'entry-trail': EntryTrail,
  'talking-points': TalkingPoints,
  'big-figures': BigFigures,
  'ood-who-paid': OodWhoPaid,
  'ood-composition': OodComposition,
}
