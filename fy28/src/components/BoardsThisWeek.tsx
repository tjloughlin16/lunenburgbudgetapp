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
export type Join = { zoom?: string | null; facebook?: string | null; youtube?: string | null; meeting_id?: string | null; passcode?: string | null; phone?: string | null; facebook_live?: string | null; facebook_live_url?: string | null }
type Notice = { board_slug: string; date: string; hook?: string; time?: string; where?: string; attend?: string; one_line: string; items: PreviewItem[]; important?: number; nothing_of_note?: boolean; agenda_url: string; join?: Join | null }

/** HOW TO JOIN, as the agenda prints it. TJ: "post the facebook and zoom links ... so
 *  people can very easily find the way to join those -- IF those links are posted in the
 *  agenda." Buttons for a Zoom link, a Facebook or YouTube address, and the dial-in; the
 *  meeting ID and passcode beside them. Where the agenda says the meeting is on Facebook
 *  Live on the Public Access page without printing an address, the button links PACC's
 *  page from the town's own listing and says it is per the agenda. Nothing here is
 *  inferred: no link on the agenda, no button. */
export function JoinLinks({ j, compact }: { j?: Join | null; compact?: boolean }) {
  if (!j) return null
  const B = ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
      className="inline-flex items-center px-2.5 py-1 rounded-md text-[12px] font-bold"
      style={{ background: 'var(--text-primary)', color: 'var(--surface-1)' }}>{children}</a>
  )
  const fb = j.facebook || j.facebook_live_url
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${compact ? 'mt-1.5' : 'mt-2'}`}>
      {j.zoom && <B href={j.zoom}>Join on Zoom ↗</B>}
      {fb && <B href={fb}>{j.facebook ? 'Facebook ↗' : 'Facebook Live ↗'}</B>}
      {j.youtube && <B href={j.youtube}>YouTube ↗</B>}
      {!compact && j.meeting_id && <span className="text-[11.5px] tnum" style={{ color: 'var(--text-secondary)' }}>Meeting ID {j.meeting_id}</span>}
      {!compact && j.passcode && <span className="text-[11.5px] tnum" style={{ color: 'var(--text-secondary)' }}>· passcode {j.passcode}</span>}
      {!compact && j.phone && <span className="text-[11.5px] tnum" style={{ color: 'var(--text-secondary)' }}>· by phone {j.phone}</span>}
      {!compact && !j.facebook && j.facebook_live_url && <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>· Facebook Live on the Public Access page, per the agenda</span>}
    </div>
  )
}
type Notices = { upcoming: Notice[] }
type Recorded = { meetings: { slug: string; board_slug: string; date: string; counts: Record<string, number> }[] }

export const THE_THREE: [string, string][] = [
  ['select-board', 'Select Board'],
  ['finance-committee', 'Finance Committee'],
  ['school-committee', 'School Committee'],
]

/** THE DAY, RELATIVE TO THE READER'S TODAY, AND ALWAYS THE WEEKDAY AND DATE. TJ, 15
 *  September 2026: "I see 'tomorrow' for something that is very much today (and we always
 *  need to show the day of the week and the date)." The payload carries the day it was
 *  built; a page read two days later must not call that day "today". So 'today' is the
 *  browser's clock, and the label is "Today, Tue Sep 15" -- never a bare "Tomorrow". */
// THE DATE LOGIC LIVES IN ../lib/meetings.ts, and these three lines are the whole reason:
// there were two copies of `todayIso` in this codebase before 25 September 2026 -- this one
// and a third about to be written -- and seven components deciding for themselves whether a
// meeting had happened. One comparison, one home, re-exported here only so the pages that
// already import from this file keep working.
// IMPORTED for this file's own use AND re-exported for the pages that already import these
// from here. A bare `export ... from` does NOT bring the names into this module's scope --
// it only forwards them -- so the first attempt at this compiled to `Cannot find name
// 'todayIso'` in six places inside this very file.
import { todayIso, dayLabel, daysAway } from '../lib/meetings'
// `daysFromToday` is what three pages already import from here, so the old name is kept as
// the exported one while the library owns the single implementation.
const daysFromToday = daysAway
export { todayIso, dayLabel, daysFromToday }

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
 *  /meeting-minutes, and it is contextual: somebody reading Tuesday's hook is exactly the
 *  person who wants to know what happened last time. */
function LastTime({ slug, rec }: { slug: string; rec: Recorded | null }) {
  const last = rec?.meetings.filter(m => m.board_slug === slug).sort((a, b) => b.date.localeCompare(a.date))[0]
  if (!last) return null
  const c = last.counts
  return (
    <a className="text-[12px] underline" href={`/meeting-minutes/${last.slug}`} style={{ color: 'var(--text-secondary)' }}>
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
    const ms = f.upcoming.meetings.filter(m => m.board_slug === slug && m.date >= todayIso() && daysFromToday(m.date) <= days).sort((a, b) => a.date.localeCompare(b.date))
    if (ms.length === 0) quiet.push(name)
    for (const m of ms) rows.push({ name, m, p: notices.d?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date) })
  }
  return (
    /* A CARD PER MEETING, on the phone. TJ, 25 September 2026, looking at this on mobile:
     * *"the meetings dont look discrete enough. just seems like text on a page, not a
     * 'thing' packaged together... maybe the meetings need some type of wrapper."*
     *
     * The principle is COMMON REGION: a shared enclosure groups a block far more strongly
     * than proximity or a divider does. These rows were separated by a 1px hairline -- the
     * weakest grouping signal there is -- directly below the FY28 budget card, which has a
     * border and a coloured left edge and therefore reads as an object. Same page, two
     * different amounts of "thingness", and the meetings lost.
     *
     * AND THE TITLE LINE WAS WRAPPING. The board name and the date shared one line with a
     * left margin, so on a 390px screen `School Committee  Today · Fri, Sep 25 9:30 a.m.`
     * broke mid-date and a title-plus-label read as a run-on sentence. The date is its own
     * line now -- an eyebrow above the name -- so it cannot collide with it at any width.
     *
     * The card, the radius and the 4px left edge are the ones the budget card already uses.
     * A new visual vocabulary for one list would be a second way of saying "this is a
     * thing", which is the problem rather than the fix. */
    <ul className="space-y-2">
      {rows.map(({ name, m, p }) => (
        <li key={m.file_id}>
          <a href={`/this-week#m-${m.board_slug}-${m.date}`}
            className="card px-3.5 py-3 block transition-opacity hover:opacity-90"
            style={{ borderLeft: '4px solid var(--series-cost)' }}>
            <span className="block text-[11.5px] font-bold uppercase tracking-widest"
              style={{ color: 'var(--series-cost)' }}>
              {dayLabel(m.date, f.as_of)}{p?.time && p.time !== 'not stated' ? ` \u00b7 ${p.time}` : ''}
            </span>
            <span className="block text-[15px] font-bold leading-tight mt-0.5">{name}</span>
            {(p?.hook || p?.one_line) && (
              <span className="block text-[13px] mt-1 leading-snug" style={{ color: 'var(--text-secondary)' }}>
                {p!.hook || p!.one_line}
              </span>
            )}
          </a>
        </li>
      ))}
      {quiet.length > 0 && (
        /* OUTSIDE THE CARDS, deliberately. "Nothing posted" is the absence of a meeting and
         * must not be dressed as one -- a dashed, unfilled row says not-a-thing at a
         * glance, which is the same distinction the cards above are drawing. */
        <li className="px-3.5 py-2 text-[12.5px] rounded-xl"
          style={{ color: 'var(--text-muted)', border: '1px dashed var(--grid)' }}>
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
    f.upcoming.meetings.filter(m => m.board_slug === slug && m.date >= todayIso() && daysFromToday(m.date) <= days).sort((a, b) => a.date.localeCompare(b.date))
  const previewFor = (m: Upcoming) => notices.d?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date)
  return (
    <ol className="space-y-2">
      {THE_THREE.map(([slug, name]) => {
        const ms = byBoard(slug)
        if (ms.length === 0) {
          return (
            <li key={slug} className="flex flex-wrap items-baseline gap-x-3 px-3 py-2 rounded-lg"
              style={{ border: '1px dashed var(--grid)' }}>
              <a href={`/boards/${slug}`} className="text-[13px] font-semibold w-36 shrink-0 underline decoration-dotted" title={`Everything about the ${name}`}>{name}</a>
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
                {/* The board's own page, from the expanded card only: the compact card is
                    itself a link, and an anchor inside an anchor is invalid HTML. */}
                {compact ? <span className="text-[13px] font-semibold w-36 shrink-0">{name}</span>
                  : <a href={`/boards/${slug}`} className="text-[13px] font-semibold w-36 shrink-0 underline decoration-dotted" title={`Everything about the ${name}`}>{name}</a>}
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
              {/* Outside the Row: on the compact card the Row is itself a link, and a
                  button inside a link is a button nobody can press. */}
              {p?.join && <div className={indent}><JoinLinks j={p.join} compact={compact} /></div>}
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
