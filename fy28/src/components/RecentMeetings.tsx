import { useReport } from './report'
import { splitMeetings, todayIso } from '../lib/meetings'

/** RECENT MEETINGS: what we have for each, whatever that is.
 *
 *  TJ, 16 September 2026, the morning after a Select Board meeting that the front page
 *  could not show: "'what was said' should show what we DO have. Youtube link? Official
 *  minutes? our own minutes? and then if we have our own minutes, the summary as you
 *  have it now ... links so people can go watch the video quickly if they want ... last
 *  7 days."
 *
 *  So: every meeting of the three boards in the last `days` days, newest first, each
 *  with the links that exist for it -- the recording, the agenda, the town's minutes,
 *  our minutes -- and, where our minutes exist, their one-line headline. A meeting held
 *  last night shows up this morning with its agenda and, once posted, its recording;
 *  the headline arrives when the minutes are written. Nothing waits on the pipeline.
 *
 *  Read from boards.json, which the daily refresh rebuilds from the town's postings.
 *  If fewer than `min` meetings fall inside the window (a quiet fortnight in August),
 *  the most recent ones fill it, so the block is never empty. */

type Recent = {
  date: string; agenda_doc?: string | null; agenda_url?: string | null
  minutes_doc?: string | null; minutes_url?: string | null; video_url?: string | null
  transcript?: boolean; captions_disabled?: boolean
  ours?: { slug: string; headline?: string; votes?: number } | null
}
type Board = { slug: string; name: string; the_three?: boolean; meetings: Recent[] }
type Boards = { as_of: string; boards: Board[] }

const fmt = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

function pending(r: Recent): string {
  if (r.ours) return ''
  if (r.video_url && r.captions_disabled) return 'captions are off on the recording, so our minutes cannot be written from it'
  if (r.video_url) return 'our minutes follow once the recording has been read'
  return 'recording not posted yet'
}

export function RecentMeetings({ days = 7, min = 3, compact = false }: { days?: number; min?: number; compact?: boolean }) {
  const { d } = useReport<Boards>('boards.json')
  if (!d) return null
  // WHICH MEETINGS HAVE HAPPENED IS DECIDED HERE, from the reader's clock, over the one
  // dated list the payload carries. This used to read a pre-split `recent` that the
  // generator built against the BUILD date -- so a meeting held after the last deploy was
  // in neither list and appeared nowhere. See ../lib/meetings.ts.
  //
  // `toISOString()` IS GONE FROM THE CUTOFF TOO: it converts to UTC first, which rolls the
  // date forward after 8pm for a reader in Lunenburg and would drop a meeting held that
  // evening out of a 7-day window.
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const cutoff = new Date(today); cutoff.setDate(cutoff.getDate() - days)
  const all = d.boards.filter(b => b.the_three)
    .flatMap(b => splitMeetings(b.meetings).past.map(r => ({ board: b.name, slug: b.slug, r })))
    .sort((a, b) => b.r.date.localeCompare(a.r.date))
  const inWindow = all.filter(x => x.r.date >= todayIso(cutoff))
  const rows = inWindow.length >= min ? inWindow : all.slice(0, min)
  if (!rows.length) return null
  const link = 'underline'
  return (
    <ol className={compact ? 'space-y-2' : 'space-y-3'} aria-label="Recent meetings">
      {rows.map(({ board, slug, r }) => (
        <li key={slug + r.date} className={compact ? 'lg:card lg:px-3 lg:py-2.5 py-2' : 'card px-4 py-3'}
          style={compact ? { borderTop: '1px solid var(--grid)' } : undefined}>
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            {r.ours
              ? <a className={`text-[13px] font-semibold ${link}`} href={`/meeting-minutes/${r.ours.slug}`} style={{ color: 'var(--series-cost)' }}>{board}, {fmt(r.date)}</a>
              : <a className={`text-[13px] font-semibold ${link}`} href={`/boards/${slug}`} style={{ color: 'var(--series-cost)' }}>{board}, {fmt(r.date)}</a>}
            {r.ours && typeof r.ours.votes === 'number' && (
              <span className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{r.ours.votes} vote{r.ours.votes === 1 ? '' : 's'}</span>
            )}
          </div>
          {/* WHAT WE HAVE, as links, IN THE ORDER WE WANT THEM USED. TJ, 17 September
              2026: "our meetings should be the most obvious clickable thing and come
              first. then the video. then the agenda." Our minutes are the thing this
              site adds -- a reader who takes one link should take that one -- so they
              lead, set bolder; the recording next; the agenda and the town's minutes
              after. The town's minutes are the record; they are not the thing we are
              asking anybody to read first. */}
          <p className="text-[12px] mt-0.5 flex flex-wrap gap-x-2" style={{ color: 'var(--text-secondary)' }}>
            {r.ours && <a className={`${link} font-semibold`} href={`/meeting-minutes/${r.ours.slug}`} style={{ color: 'var(--series-cost)' }}>read our minutes &rarr;</a>}
            {r.video_url && <>{r.ours ? '· ' : ''}<a className={link} href={r.video_url} target="_blank" rel="noreferrer">&#9654; watch the recording</a></>}
            {r.agenda_doc && <>{r.ours || r.video_url ? '· ' : ''}<a className={link} href={r.agenda_doc}>agenda</a></>}
            {(r.minutes_doc || r.minutes_url) && <>· <a className={link} href={r.minutes_doc || r.minutes_url!}>the town&rsquo;s minutes</a></>}
          </p>
          {r.ours?.headline
            ? <p className="text-[13px] mt-1 leading-snug">{r.ours.headline}</p>
            : <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>{pending(r)}</p>}
        </li>
      ))}
    </ol>
  )
}
