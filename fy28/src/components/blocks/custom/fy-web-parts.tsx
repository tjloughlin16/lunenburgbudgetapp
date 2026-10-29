/** WHAT THE WEB OF A YEAR AND AN ITEM'S OWN WEB SHARE (fy-web.tsx, fy-ego-web.tsx): the file's
 *  shape, one colour per kind of arrow, the arrowheads, and the curve. One copy, so the isolated
 *  web on a line's or a fund's page draws an arrow exactly as the big web does.
 *  The data is /data/fy-breakdown/web-<year>.json (scripts/fy_web.py); an item's page carries the
 *  arrows of that file that touch it (scripts/fy_items.py). */
import { PAYER } from './fy-shared'

export type WebKind = 'school' | 'paid' | 'later' | 'back' | 'kind' | 'none' | 'capital' | 'between' | 'fund' | 'transfer'
export type WebNode = { id: string; kind: 'fund' | 'line' | 'sink'; label: string; group?: string; sub?: string; cat?: string; cid?: string
  /** the node's own page, where it has one (fy_items.py) */
  href?: string }
export type WebEdge = { a: string; b: string; k: WebKind; v: number; t: string; d?: string; m?: string }
export type WebFile = { fy: number; nodes: WebNode[]; edges: WebEdge[] }

export const WEB_COLOUR: Record<WebKind, string> = {
  school: 'var(--text-muted)', paid: 'var(--thread-2)', later: 'var(--thread-3)', back: 'var(--thread-1)',
  kind: 'var(--thread-5)', none: 'var(--thread-4)', capital: 'var(--thread-4)', between: 'var(--thread-4)', fund: 'var(--thread-5)',
  transfer: 'var(--thread-6, var(--text-secondary))' }

/** A fund's block takes its payer's colour; a place money lands on no line is grey. */
export const nodeFill = (n: WebNode) => n.kind === 'fund' ? (PAYER[n.group ?? ''] ?? 'var(--text-secondary)')
  : n.kind === 'sink' ? 'var(--text-muted)' : 'var(--surface-2)'

export const cut = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s)

/** One arrowhead per kind, ids prefixed so two webs on one page do not share them. */
export function WebMarkers({ prefix }: { prefix: string }) {
  return (
    <defs>
      {(Object.keys(WEB_COLOUR) as WebKind[]).map(k => (
        <marker key={k} id={`${prefix}-${k}`} viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill={WEB_COLOUR[k]} /></marker>))}
    </defs>)
}

/** A horizontal S-curve from (x1, y1) to (x2, y2), its handles `bend` out from each end. A
 *  negative `bend` runs right to left (an arrow back to the fund column). */
export const curve = (x1: number, y1: number, x2: number, y2: number, bend: number) =>
  `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`

/** An arrow's width: square root of its share of the largest, so a hairline still shows. By size:
 *  a refund or a reversal is an arrow below zero, and draws as wide as its amount. */
export const edgeWidth = (v: number, max: number, school = false) =>
  school ? 0.6 + 5 * Math.sqrt(Math.abs(v) / max) : 1 + 13 * Math.sqrt(Math.abs(v) / max)
