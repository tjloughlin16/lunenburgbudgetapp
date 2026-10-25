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
import SerfMoneyStack from './serf-money-stack'

export type CustomProps = { data: unknown; alt: string }

export const CUSTOM_BLOCKS: Record<string, ComponentType<CustomProps>> = {
  'serf-money-stack': SerfMoneyStack,
}
