import { useEffect, useState } from 'react'

/** WHICH ORG CHART A BOARD OR DEPARTMENT HAS, from the published join.
 *
 *  TJ, 10 October 2026: *"do the board/dept have an org chart link!? I cant find it"*. The
 *  org chart linked TO the board and money pages (scripts/build_body_crosswalk.py), and
 *  nothing linked back from a board's own page. The join already exists and is published --
 *  `/docs/data/body-crosswalk.csv`, 16 KB -- so this reads it rather than building a second
 *  copy of a decision that file makes, with its basis, in one place.
 *
 *  A body matches on `board_slug` or `money_slug` (a board's page slug and its finance slug
 *  are the same string). Several units can match -- a board and its staff are two charts --
 *  and all are returned. Fetched once per page view and cached for the session. */
export type ChartLink = { unit: string; chart_url: string; last_fy: string; people: string }

let cache: Promise<Record<string, string>[]> | null = null

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []
  let row: string[] = [], cell = '', q = false
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (q) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++ }
      else if (c === '"') q = false
      else cell += c
    } else if (c === '"') q = true
    else if (c === ',') { row.push(cell); cell = '' }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++
      row.push(cell); rows.push(row); row = []; cell = ''
    } else cell += c
  }
  if (cell || row.length) { row.push(cell); rows.push(row) }
  const [head, ...body] = rows
  return body.filter(r => r.length === head.length).map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])))
}

export function useOrgCharts(slug: string): ChartLink[] {
  const [out, setOut] = useState<ChartLink[]>([])
  useEffect(() => {
    cache ??= fetch('/docs/data/body-crosswalk.csv').then(r => (r.ok ? r.text() : '')).then(parseCsv).catch(() => [])
    let live = true
    cache.then(rows => {
      if (!live) return
      setOut(rows.filter(r => r.board_slug === slug || r.money_slug === slug)
        .map(r => ({ unit: r.unit, chart_url: r.chart_url, last_fy: r.last_fy, people: r.people_last_fy })))
    })
    return () => { live = false }
  }, [slug])
  return out
}
