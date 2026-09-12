import { useReport } from './report'

/** THE THREE BOARDS, AT A GLANCE. Used on the front page and at the top of /this-week.
 *
 *  TJ, 12 September 2026: separate the three boards people care about from the rest
 *  "so people can see when there is a meeting of any of the 3 very quickly"; give each
 *  meeting a HOOK rather than a dump; put the time and place on the listing as chips;
 *  collapse the detail.
 *
 *  One row per meeting: day · board · hook. Under it, chips for time, place and how to
 *  attend, and an agenda link. The item-by-item detail sits behind a <details>, closed.
 *  Everything shown comes from the town's agenda via the preview -- the hook names what
 *  is ON the agenda and predicts nothing. A board with no meeting in the window says so,
 *  which is the fast answer the row exists to give. */

type Upcoming = { agenda_url: string; board: string; board_slug: string; date: string; days_away: number; file_id: string }
type Feed = { as_of: string; upcoming: { horizon_days: number; meetings: Upcoming[] } }
type PreviewItem = { agenda_line: string; why_it_matters: string; kind: string; vote_expected?: boolean; important?: boolean }
type Notice = { board_slug: string; date: string; hook?: string; time?: string; where?: string; attend?: string; one_line: string; items: PreviewItem[]; important?: number; nothing_of_note?: boolean; agenda_url: string }
type Notices = { upcoming: Notice[] }

export const THE_THREE: [string, string][] = [
  ['select-board', 'Select Board'],
  ['finance-committee', 'Finance Committee'],
  ['school-committee', 'School Committee'],
]

function dayLabel(iso: string, asOf: string) {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  const [ay, am, ad] = asOf.split('-').map(Number)
  const diff = Math.round((date.getTime() - new Date(ay, am - 1, ad).getTime()) / 86400000)
  const wd = date.toLocaleDateString('en-US', { weekday: 'long' })
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff < 7) return wd
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

function Chip({ children, tone }: { children: React.ReactNode; tone?: 'strong' }) {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded text-[11px] whitespace-nowrap"
      style={{ background: tone === 'strong' ? 'var(--text-primary)' : 'var(--surface-3)',
               color: tone === 'strong' ? 'var(--surface-1)' : 'var(--text-secondary)' }}>{children}</span>
  )
}

export function BoardsThisWeek({ days = 14, compact = false }: { days?: number; compact?: boolean }) {
  const feed = useReport<Feed>('meeting-feed.json')
  const notices = useReport<Notices>('notices.json')
  const f = feed.d
  if (!f) return null
  const byBoard = (slug: string) =>
    f.upcoming.meetings.filter(m => m.board_slug === slug && m.days_away <= days).sort((a, b) => a.date.localeCompare(b.date))
  const previewFor = (m: Upcoming) => notices.d?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date)
  return (
    <ol className="space-y-2">
      {THE_THREE.map(([slug, name]) => {
        const ms = byBoard(slug)
        if (ms.length === 0) {
          return (
            <li key={slug} className="flex flex-wrap items-baseline gap-x-3 px-3 py-2 rounded-lg"
              style={{ border: '1px dashed var(--grid)' }}>
              <span className="text-[13px] font-semibold w-36 shrink-0">{name}</span>
              <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>no meeting posted in the next {days} days</span>
            </li>
          )
        }
        return ms.map(m => {
          const p = previewFor(m)
          const hook = p?.hook || p?.one_line
          return (
            <li key={m.file_id} className="card px-3 py-2.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <span className="text-[13px] font-semibold w-36 shrink-0">{name}</span>
                <span className="text-[13px] font-bold" style={{ color: 'var(--series-cost)' }}>{dayLabel(m.date, f.as_of)}</span>
                {p?.time && p.time !== 'not stated' && <Chip tone="strong">{p.time}</Chip>}
                {p?.where && p.where !== 'not stated' && <Chip>{p.where}</Chip>}
                {p?.attend && p.attend !== 'not stated' && <Chip>{p.attend}</Chip>}
                <a className="text-[11.5px] underline ml-auto" style={{ color: 'var(--text-muted)' }}
                  href={m.agenda_url} target="_blank" rel="noreferrer">agenda</a>
              </div>
              {hook && (
                <p className="text-[13.5px] mt-1 leading-snug sm:pl-[9.75rem]">{hook}</p>
              )}
              {/* WHAT MATTERS, FLAGGED. TJ: "if there is anything in there that is
                  'important' (think, schools, budgets, citizen-facing impact) then lets
                  highlight that. And if there's NOTHING important, we probably need to
                  show that". Important items come first with a mark; a meeting with
                  none says so in plain words rather than leaving a blank. */}
              {p && p.items.length > 0 && !p.items.some(it => it.important) && (
                <p className="text-[12px] mt-1 sm:pl-[9.75rem]" style={{ color: 'var(--text-muted)' }}>
                  Routine business — nothing on this agenda changes a bill, a school or a service.
                </p>
              )}
              {!compact && p && p.items.length > 0 && (
                <details className="mt-1 sm:pl-[9.75rem]">
                  <summary className="text-[12px] cursor-pointer" style={{ color: 'var(--series-cost)' }}>
                    {(() => { const n = p.items.filter(it => it.important).length
                      return n ? `${n} item${n === 1 ? '' : 's'} that matter, and ${p.items.length - n} more` : `${p.items.length} items of note` })()}
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {[...p.items].sort((a, b) => Number(!!b.important) - Number(!!a.important)).map((it, i) => (
                      <li key={i} className="text-[13px] flex gap-2 items-baseline"
                        style={it.important ? { borderLeft: '3px solid var(--series-revenue, #b5540f)', paddingLeft: 8 } : { paddingLeft: 11 }}>
                        <span className="text-[10px] font-bold uppercase tracking-widest whitespace-nowrap w-16 shrink-0"
                          style={{ color: it.vote_expected ? 'var(--series-cost)' : 'var(--text-muted)' }}>{it.vote_expected ? 'vote' : it.kind}</span>
                        <span><span className={it.important ? 'font-semibold' : 'font-medium'}>{it.agenda_line.replace(/^[a-z0-9]+\.\s*/i, '')}</span>
                          <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}> — {it.why_it_matters}</span></span>
                      </li>
                    ))}
                  </ul>
                  <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>Quoted from the agenda; an agenda lists what may be discussed, not what will be decided.</p>
                </details>
              )}
            </li>
          )
        })
      })}
    </ol>
  )
}
