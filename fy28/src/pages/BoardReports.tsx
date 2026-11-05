import { BoardNav } from '../components/BoardNav'
import type { Tab } from '../routes'
import { boardReportsSlugFromPath } from '../routes'
import { H2, ReportShell, useReport } from '../components/report'

const TAB: Tab = 'boards'
const DATA = '/data/topics.json'

/** A BOARD'S REPORTS, /boards/<slug>/reports. TJ, 5 November 2026: "i need to be able to find
 *  these reports from the board page". Every shelf the registry gives this board, with its pages
 *  (scripts/topics.py, board_of). A board with one shelf of its own lives at this address instead:
 *  routes.ts sends that to the hub, so this page only draws boards that have several. */
type Category = { id: string; title: string; path: string; answer: string | null; ready: boolean; board?: string
  groups: { title: string | null; topics: string[] }[] }
type Index = { categories: Category[]; topics: Record<string, { title: string; path: string; ready: boolean }> }

export function BoardReports() {
  const slug = boardReportsSlugFromPath(window.location.pathname) ?? ''
  const { d, err } = useReport<Index>('topics.json')
  const { d: nav } = useReport<{ boards: { slug: string; name: string }[] }>('boards-nav.json')
  if (!d) return <ReportShell tab={TAB} title="Reports" err={err} loading={!err} dataUrl={DATA} />
  const shelves = d.categories.filter(c => c.board === slug && c.ready)
  const name = nav?.boards.find(x => x.slug === slug)?.name ?? ''
  return (
    <ReportShell tab={TAB} title={`${name} — reports`} dataUrl={DATA}>
      <BoardNav slug={slug} current="reports" />
      {shelves.length === 0 && <p className="mt-6 text-sm">No reports are filed under this board.</p>}
      {shelves.map(c => (
        <section key={c.id} className="mt-8 max-w-3xl">
          <H2><a className="underline" href={c.path}>{c.title}</a></H2>
          {c.answer && <p className="text-[14px] mt-1" style={{ color: 'var(--text-secondary)' }}>{c.answer}</p>}
          {c.groups.map(g => {
            const pages = g.topics.map(t => d.topics[t]).filter(t => t && t.ready)
            return pages.length === 0 ? null : (
              <div key={g.title ?? 'pages'} className="mt-3">
                {g.title && <p className="text-[13px] font-semibold">{g.title}</p>}
                <ul className="m-0 mt-1 p-0 list-none text-[14px] flex flex-wrap gap-x-4 gap-y-1">
                  {pages.map(t => <li key={t.path}><a className="underline" href={t.path}>{t.title}</a></li>)}
                </ul>
              </div>
            )
          })}
        </section>
      ))}
    </ReportShell>
  )
}
