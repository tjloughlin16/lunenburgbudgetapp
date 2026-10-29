/** ONE PAGE PER SCHOOL LINE AND PER FUND: the index of them, /data/fy-breakdown/index.json
 *  (scripts/fy_items.py), and the address of each. Read by the line and fund popups (their "Link
 *  to this page"), the web of a year (its blocks link to their pages) and the pages themselves. */
import { useEffect, useState } from 'react'

export type ItemLine = { slug: string; name: string; account: string; cat: string; years: string[] }
export type ItemFund = { slug: string; name: string; cat: string; group: string; funds: string[]; years: string[] }
export type ItemIndex = {
  lines: ItemLine[]; funds: ItemFund[]; years: string[]; span: string
  /** lines read together, /school-groups/<slug> */
  groups?: { slug: string; name: string; members: string[]; funds: string[] }[]
  sources: { href: string; label: string }[]
  frame: { line: Record<string, unknown>; fund: Record<string, unknown>; web: Record<string, unknown>; moves: Record<string, unknown> }
  text: Record<string, string>
}

export const LINE_BASE = '/school-lines/'
export const FUND_BASE = '/school-funds/'
export const GROUP_BASE = '/school-groups/'

let INDEX: Promise<ItemIndex> | null = null
export const loadIndex = () => {
  if (!INDEX) INDEX = fetch('/data/fy-breakdown/index.json')
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
  return INDEX
}

/** The index, once it has loaded; null until then or if it cannot be. */
export function useItemIndex(): ItemIndex | null {
  const [ix, setIx] = useState<ItemIndex | null>(null)
  useEffect(() => { let live = true; loadIndex().then(v => { if (live) setIx(v) }, () => {}); return () => { live = false } }, [])
  return ix
}

/** Account -> its page, and fund number -> its programme's page. */
export function itemHrefs(ix: ItemIndex | null) {
  const line = new Map<string, string>(), fund = new Map<string, string>()
  for (const l of ix?.lines ?? []) line.set(l.account, LINE_BASE + l.slug)
  for (const f of ix?.funds ?? []) for (const n of f.funds) fund.set(n, FUND_BASE + f.slug)
  return {
    line: (account: string) => line.get(account),
    fund: (fund_: string) => fund.get(fund_),
    /** a block of the web: `l:<account>` or `f:<fund>` */
    node: (id: string) => id.startsWith('l:') ? line.get(id.slice(2)) : id.startsWith('f:') ? fund.get(id.slice(2)) : undefined,
  }
}

/** /school-lines/<slug>, /school-funds/<slug> or /school-groups/<slug> (lines read together), or null. */
export function itemFromPath(pathname: string): { kind: 'line' | 'fund' | 'group'; slug: string } | null {
  const m = /^\/school-(lines|funds|groups)\/([a-z0-9-]+)\/?$/.exec(pathname.toLowerCase())
  return m ? { kind: m[1] === 'lines' ? 'line' : m[1] === 'funds' ? 'fund' : 'group', slug: m[2] } : null
}

/** A link to the page, carrying the year being read. */
export const withYear = (href: string, fy: string) => `${href}?fy=${encodeURIComponent(fy)}`
