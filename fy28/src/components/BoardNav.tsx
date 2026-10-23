import { useReport } from './report'
import { useBoardTransfers } from '../pages/BoardTransfers'
import { useOrgCharts } from '../lib/orgChartLink'

/** A BOARD'S TABS -- the local navigation of the hub and its spokes.
 *
 *  TJ, 11 October 2026: *"we've outgrown the sidebar model for the board and commission
 *  pages ... the main content actually is heavily in those sidebars ... pull those links
 *  out of the sidebar and create a main page for all the boards, for each board
 *  individually."* The sidebar was the only way to reach Finance, Transfers, Records and
 *  the org chart, and on a phone it sat behind a floating button. So every board page --
 *  the overview and each spoke -- opens with the same row of tabs, and a tab exists only
 *  where the board has something on it: of sixty boards, most have no votes or finance.
 *
 *  Reads `boards-nav.json` (build_boards.nav, ~11 KB), never boards.json (~15 MB): this bar
 *  sits on Finance, Records and Transfers too, which never needed the big payload. */
export type BoardTab = 'overview' | 'meetings' | 'votes' | 'time' | 'schedule' | 'finance' | 'transfers' | 'records' | 'about'

type Nav = { boards: { slug: string; name: string; votes: number; time: boolean; schedule: boolean; finance: boolean; about: boolean }[] }

export function BoardNav({ slug, current }: { slug: string; current: BoardTab }) {
  const { d } = useReport<Nav>('boards-nav.json')
  const transfers = useBoardTransfers(slug)
  const charts = useOrgCharts(slug)
  const b = d?.boards.find(x => x.slug === slug)
  if (!b) return null
  const base = `/boards/${slug}`
  const tabs: { key: BoardTab | 'people'; href: string; label: string; show: boolean }[] = [
    { key: 'overview', href: base, label: 'Overview', show: true },
    { key: 'meetings', href: `${base}/meetings`, label: 'Meetings', show: true },
    { key: 'votes', href: `${base}/votes`, label: `All votes`, show: b.votes > 0 },
    { key: 'time', href: `${base}/time`, label: 'Time', show: b.time },
    { key: 'schedule', href: `${base}/schedule`, label: 'Budget schedule', show: b.schedule },
    { key: 'finance', href: `${base}/finance`, label: 'Finance', show: b.finance },
    { key: 'transfers', href: transfers?.url ?? `${base}/transfers`, label: 'Transfers', show: !!transfers },
    // The org chart lives in its own section of the site, so this tab leaves the board.
    // A board drawn twice (the board and the office that staffs it) opens on the first;
    // About lists both.
    { key: 'people', href: charts[0]?.chart_url ?? '', label: 'People ↗', show: charts.length > 0 },
    { key: 'records', href: `${base}/records`, label: 'Missing records', show: true },
    { key: 'about', href: `${base}/about`, label: 'About', show: b.about },
  ]
  return (
    <nav aria-label={`${b.name} pages`} className="no-print mt-5 -mx-1 overflow-x-auto">
      <ul className="flex gap-1 px-1 pb-1 m-0 list-none whitespace-nowrap" style={{ borderBottom: '1px solid var(--grid)' }}>
        {tabs.filter(t => t.show).map(t => {
          const on = t.key === current
          return (
            <li key={t.key}>
              <a href={t.href} aria-current={on ? 'page' : undefined}
                className="block px-3 py-2 text-[13.5px] font-semibold no-underline rounded-t-md"
                style={{
                  color: on ? 'var(--text-primary)' : 'var(--text-secondary)',
                  boxShadow: on ? 'inset 0 -2px 0 var(--series-cost)' : undefined,
                }}>
                {t.label}{t.key === 'votes' ? <span className="ml-1 font-normal tnum" style={{ color: 'var(--text-muted)' }}>{b.votes.toLocaleString('en-US')}</span> : null}
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
