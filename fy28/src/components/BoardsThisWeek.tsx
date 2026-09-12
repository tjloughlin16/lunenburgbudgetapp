import { useEffect } from 'react'
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
type Recorded = { meetings: { slug: string; board_slug: string; date: string; counts: Record<string, number> }[] }

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

function shortDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/** "Last time" -- the board's most recent meeting we have minutes for. THE FIRST LINK to
 *  /what-was-said, and it is contextual: somebody reading Tuesday's hook is exactly the
 *  person who wants to know what happened last time. */
function LastTime({ slug, rec }: { slug: string; rec: Recorded | null }) {
  const last = rec?.meetings.filter(m => m.board_slug === slug).sort((a, b) => b.date.localeCompare(a.date))[0]
  if (!last) return null
  const c = last.counts
  return (
    <a className="text-[12px] underline" href={`/what-was-said/${last.slug}`} style={{ color: 'var(--text-secondary)' }}>
      last time ({shortDate(last.date)}): {c.votes} vote{c.votes === 1 ? '' : 's'}{c.transfers ? `, ${c.transfers} transfer${c.transfers === 1 ? '' : 's'}` : ''} &rarr;
    </a>
  )
}

/** THE PHONE STRIP. TJ, on the front page on a phone: "Feels overwhelming and the styling
 *  doesn't help my eye figure out what I'm looking at." Three cards with chips, hooks and
 *  links, all at one weight, before any orientation. On a phone the same information is
 *  one line per board -- board, day, time, hook -- and the boards with nothing are one
 *  muted line together. The row is the link. */
export function BoardsStrip({ days = 7 }: { days?: number }) {
  const feed = useReport<Feed>('meeting-feed.json')
  const notices = useReport<Notices>('notices.json')
  const f = feed.d
  if (!f) return null
  const rows: { name: string; m: Upcoming; p?: Notice }[] = []
  const quiet: string[] = []
  for (const [slug, name] of THE_THREE) {
    const ms = f.upcoming.meetings.filter(m => m.board_slug === slug && m.days_away <= days).sort((a, b) => a.date.localeCompare(b.date))
    if (ms.length === 0) quiet.push(name)
    for (const m of ms) rows.push({ name, m, p: notices.d?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date) })
  }
  return (
    <ul>
      {rows.map(({ name, m, p }) => (
        <li key={m.file_id} style={{ borderBottom: '1px solid var(--grid)' }}>
          <a href={`/this-week#m-${m.board_slug}-${m.date}`} className="block py-2.5">
            <span className="text-[13.5px] font-semibold">{name}</span>
            <span className="text-[13px] font-semibold ml-2" style={{ color: 'var(--series-cost)' }}>{dayLabel(m.date, f.as_of)}{p?.time && p.time !== 'not stated' ? ` ${p.time}` : ''}</span>
            {(p?.hook || p?.one_line) && <span className="block text-[13px] mt-0.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>{p!.hook || p!.one_line}</span>}
          </a>
        </li>
      ))}
      {quiet.length > 0 && (
        <li className="py-2.5 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
          {quiet.join(' and ')}: nothing posted for the next {days} days.
        </li>
      )}
    </ul>
  )
}

export function BoardsThisWeek({ days = 14, compact = false }: { days?: number; compact?: boolean }) {
  const feed = useReport<Feed>('meeting-feed.json')
  const notices = useReport<Notices>('notices.json')
  const recorded = useReport<Recorded>('recording-minutes.json')
  const f = feed.d
  // A row clicked on the front page lands here with #m-<board>-<date>: that meeting's
  // detail opens and the page scrolls to it. TJ: "should bring people to the 'this
  // week' page with the meeting expanded for OUR detailed view, not just the agenda."
  const target = typeof window !== 'undefined' ? window.location.hash.replace(/^#/, '') : ''
  useEffect(() => {
    if (!compact && target && f) {
      const el = document.getElementById(target)
      if (el) el.scrollIntoView({ block: 'start' })
    }
  }, [compact, target, f])
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
              <span className="ml-auto"><LastTime slug={slug} rec={recorded.d} /></span>
            </li>
          )
        }
        return ms.map(m => {
          const p = previewFor(m)
          const hook = p?.hook || p?.one_line
          const id = `m-${m.board_slug}-${m.date}`
          // The indent lines the hook up under the day in the wide layout only. In the
          // narrow column the chips wrap and an indent leaves a dead gutter with the
          // words crushed to the right -- TJ: "This looks broken".
          const indent = compact ? '' : 'sm:pl-[9.75rem]'
          const Row = compact ? 'a' : 'div'
          return (
            <li key={m.file_id} id={id} className="card px-3 py-2.5" style={{ scrollMarginTop: 80, ...(target === id ? { borderColor: 'var(--series-cost)' } : {}) }}>
              <Row {...(compact ? { href: `/this-week#${id}`, className: 'block hover:opacity-90' } : {})}>
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <span className="text-[13px] font-semibold w-36 shrink-0">{name}</span>
                <span className="text-[13px] font-bold" style={{ color: 'var(--series-cost)' }}>{dayLabel(m.date, f.as_of)}</span>
                {p?.time && p.time !== 'not stated' && <Chip tone="strong">{p.time}</Chip>}
                {p?.where && p.where !== 'not stated' && <Chip>{p.where}</Chip>}
                {p?.attend && p.attend !== 'not stated' && <Chip>{p.attend}</Chip>}
                {!compact && <a className="text-[11.5px] underline ml-auto" style={{ color: 'var(--text-muted)' }}
                  href={m.agenda_url} target="_blank" rel="noreferrer">agenda</a>}
                {compact && <span className="text-[11.5px] ml-auto" style={{ color: 'var(--series-cost)' }}>details &rarr;</span>}
              </div>
              {hook && (
                <p className={`text-[13.5px] mt-1 leading-snug ${indent}`}>{hook}</p>
              )}
              </Row>
              <p className={`mt-1 ${indent}`}><LastTime slug={slug} rec={recorded.d} /></p>
              {/* WHAT MATTERS, FLAGGED. TJ: "if there is anything in there that is
                  'important' (think, schools, budgets, citizen-facing impact) then lets
                  highlight that. And if there's NOTHING important, we probably need to
                  show that". Important items come first with a mark; a meeting with
                  none says so in plain words rather than leaving a blank. */}
              {p && p.items.length > 0 && !p.items.some(it => it.important) && (
                <p className={`text-[12px] mt-1 ${indent}`} style={{ color: 'var(--text-muted)' }}>
                  Routine business — nothing on this agenda changes a bill, a school or a service.
                </p>
              )}
              {!compact && p && p.items.length > 0 && (
                <details className={`mt-1 ${indent}`} open={target === id}>
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
