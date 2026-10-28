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
import FyLineTable from './fy-line-table'
import FyYearFacts from './fy-year-facts'
import FyYearPicker from './fy-year-picker'
import FyOverlap from './fy-overlap'
import FyYearLine from './fy-year-line'
import FyReadiness from './fy-readiness'
import FyBridge from './fy-bridge'
import FyLineFunds from './fy-line-funds'
import FyPlan from './fy-plan'
import FySourceTable from './fy-source-table'
import FyYearWeeks from './fy-year-weeks'
import GrantAwardsStack from './grant-awards-stack'
import MeetingTrail from './meeting-trail'
import SerfMoneyStack from './serf-money-stack'
import SerfSaidLedger from './serf-said-ledger'

export type CustomProps = { data: unknown; alt: string }

export const CUSTOM_BLOCKS: Record<string, ComponentType<CustomProps>> = {
  'fy-line-table': FyLineTable,
  'fy-year-facts': FyYearFacts,
  'fy-year-picker': FyYearPicker,
  'fy-overlap': FyOverlap,
  'fy-year-line': FyYearLine,
  'fy-readiness': FyReadiness,
  'fy-bridge': FyBridge,
  'fy-line-funds': FyLineFunds,
  'fy-plan': FyPlan,
  'fy-source-table': FySourceTable,
  'fy-year-weeks': FyYearWeeks,
  'grant-awards-stack': GrantAwardsStack,
  'meeting-trail': MeetingTrail,
  'serf-money-stack': SerfMoneyStack,
  'serf-said-ledger': SerfSaidLedger,
}
