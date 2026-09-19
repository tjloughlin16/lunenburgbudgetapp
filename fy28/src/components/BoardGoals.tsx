import { useReport } from './report'
import { useState } from 'react'

/** THE GOALS A BOARD SET ITSELF, in its own words.
 *
 *  TJ, 19 September 2026: "if any boards have goals set, i want to have a stated goals
 *  section at the top of each board... oh if we ALREADY track them as threads, then map
 *  them."
 *
 *  The mapping is the interesting half. Three of the Town Manager's FY26 objectives — TC
 *  Passios, 925 Mass Ave, the Salary Administration Plan — are matters this project was
 *  already following as threads, found from the meeting record before anybody read the
 *  goals document. A goal that is already a thread needs no second progress mechanism:
 *  the thread is the progress, and the link goes there.
 *
 *  WHAT THIS DOES NOT SAY IS WHETHER A GOAL WAS MET. There is no status, no tick, no
 *  score. An objective reading "complete the sale of 925 Mass Ave within the Fiscal Year"
 *  beside a thread still open in September is two facts, and the reader draws the
 *  inference — rule 7. Scoring the town against its own goals is a different piece of
 *  work and it has not been done. */

type Objective = { no: string; text: string; thread: string }
type Goal = { no: string; goal: string; summary: string; thread: string; objectives: Objective[] }
type Owner = {
  owner: string; fy: string; basis: string; source: string; source_url: string
  adopted_on: string; adopted_at: string; adopted_url: string; current: string
  goals: Goal[]
}
type Payload = { about: string; current_fy: string; boards: Record<string, Owner[]> }

/** The owner reads "the Select Board" in a sentence and "Select Board" in a heading. The
 *  article is carried in the data because the source lines use it mid-sentence; a title
 *  drops it. */
const asTitle = (owner: string) => owner.replace(/^the\s+/i, '')

/** A goal's thread, whether it was set on the goal or on one of its objectives — the
 *  document puts "925 Mass Ave" under an objective and the School Committee puts "the
 *  future of Turkey Hill" at goal level, and a reader should not have to know which. */
const threadOf = (g: Goal) => g.thread || g.objectives.find(o => o.thread)?.thread || ''

/** ONE GOAL: a title, one line, and the board's own words behind a toggle.
 *
 *  NOT components/primitives.tsx's `Disclose`, and the reason is mechanical rather than
 *  stylistic. TJ wants the TITLE to link to the thread where one exists; Disclose puts its
 *  title inside a <button>, and an <a> nested in a <button> is invalid HTML — a screen
 *  reader is told one thing and a keyboard does another. So the two actions get two
 *  controls: the title is a link, and "Open" is a button. Where there is no thread the
 *  title is plain text and the whole row toggles, because then there is only one action
 *  and it should have the largest target. */
function GoalRow({ g, thread }: { g: Goal; thread: string }) {
  const [open, setOpen] = useState(false)
  const toggle = <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
    className="text-[11px] font-semibold shrink-0" style={{ color: 'var(--series-cost)' }}>
    {open ? 'Hide' : 'Open'}</button>
  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0">
          {thread
            ? <a href={`/threads/${thread}`} className="block text-[13px] font-bold underline">{g.goal}</a>
            : <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
                className="block text-[13px] font-bold text-left">{g.goal}</button>}
          {g.summary && !open ? (
            <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {g.summary}
            </span>
          ) : null}
        </span>
        {toggle}
      </div>
      {open ? (
        <div className="mt-3">
          {g.objectives.length ? (
            <ul className="pl-4 space-y-1.5 text-[13.5px] list-disc"
              style={{ color: 'var(--text-secondary)' }}>
              {g.objectives.map(ob => <li key={ob.no}>{ob.text}</li>)}
            </ul>
          ) : (
            <p className="text-[13.5px] m-0" style={{ color: 'var(--text-secondary)' }}>
              Set as a single goal, with no objectives recorded under it.
            </p>
          )}
          {thread ? (
            <p className="text-[13px] mt-3 mb-0">
              <a className="underline font-semibold" href={`/threads/${thread}`}>
                Follow the thread &rarr;
              </a>
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export function BoardGoals({ slug }: { slug: string }) {
  const { d } = useReport<Payload>('board-goals.json')
  const sets = d?.boards?.[slug]
  if (!sets || !sets.length) return null
  return (
    <>
      {sets.map(o => (
        <div key={o.owner} className="card p-4 mt-6 max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>
            {asTitle(o.owner)} stated goals · FY{o.fy}
            {o.current !== 'yes' ? <span style={{ color: 'var(--status-warning)' }}> · superseded</span> : null}
          </p>
          {/* EACH GOAL COLLAPSES. TJ: "they are LONG". One Select Board goal carries
              six objectives, so a page showing every one open is a wall before it is a
              list. Collapsed: the goal and one line of ours. Expanded: the board's own
              words, which is what anyone should quote. */}
          <div className="mt-3 space-y-2">
            {o.goals.map(g => <GoalRow key={g.no} g={g} thread={threadOf(g)} />)}
          </div>
          {/* WHERE THEY WERE SET, always. TJ: "we always need a link to the meeting
              where the goals were set by the board." A goals list with no adoption
              meeting is a claim about what a board committed to with nothing behind it. */}
          <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
            {o.adopted_on ? (
              <>Adopted at <a className="underline" href={o.adopted_url}>{o.adopted_at},{' '}
                {new Date(o.adopted_on + 'T12:00:00Z').toLocaleDateString('en-US',
                  { month: 'short', day: 'numeric', year: 'numeric' })}</a>. </>
            ) : (
              <>The meeting that adopted these is not in the minutes we can read. </>
            )}
            {o.basis === 'published document'
              ? <><a className="underline" href={o.source_url}>The goals document</a>. </>
              : <>Recorded in our minutes rather than a published goals document. </>}
            The one-line summaries are ours; open a goal for the board&rsquo;s own words.
            Nothing here says whether a goal was met.
          </p>
        </div>
      ))}
    </>
  )
}
