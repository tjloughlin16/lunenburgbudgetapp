/* WHETHER A MEETING HAS HAPPENED IS DECIDED WHEN SOMEBODY LOOKS, NOT WHEN THE SITE IS BUILT.
 *
 * TJ, 25 September 2026: *"i want the site to change even if I forget to deploy everyday,
 * just based on known meetings and dates already fetched on it"*, and on the shape he
 * expected: *"we have a register of meetings and dates. and they automatically shift from
 * upcoming to recent, based on dates, without a deploy, and if we get info like minutes, it
 * just 'fills in' with a deploy."*
 *
 * WHAT WENT WRONG. The generators split meetings into `upcoming` and `recent` against the
 * BUILD date, and `/data/*.json` is a static file, so nothing re-evaluated when the day
 * changed. The Finance Committee's 24 September meeting was in `upcoming` with
 * `days_away: 1` on a payload built the 23rd; the board page filters upcoming by today's
 * date, so on the 25th it was filtered out of that list and had never been in the other
 * one. It disappeared from a site whose data held it the whole time. TJ: *"i saw the finance
 * committee meeting posted yesterday and the day before. but now its gone."*
 *
 * THE RULE: the payload carries ONE dated list of known meetings; this module decides which
 * are past and which are to come, from the reader's own clock. So the shift needs no deploy.
 * A deploy is still needed for a NEW meeting or for minutes to fill in -- which is exactly
 * what a deploy should be for, and a stale payload now degrades to a meeting missing its
 * minutes rather than to a missing meeting.
 *
 * AND IT LIVES IN ONE PLACE ON PURPOSE. Seven components read these lists. Seven copies of
 * `date >= today` is the defect this project keeps meeting -- three copies of one list, one
 * of them drifted, and a page that refused to build. There is one comparison here and every
 * caller uses it.
 */

/** Today, as the reader's own device reckons it, in the `YYYY-MM-DD` the payload uses.
 *
 *  LOCAL, NOT UTC. `toISOString()` converts to UTC first, so for a reader in Lunenburg it
 *  rolls the date forward at 8pm and a meeting that evening would read as yesterday's. The
 *  town's meetings are local events and the comparison has to be local too. */
export function todayIso(now: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`
}

/** Whole days from today to a meeting date. Negative once it is past. */
export function daysAway(date: string, now: Date = new Date()): number {
  const [y, m, d] = date.split('-').map(Number)
  const then = new Date(y, (m || 1) - 1, d || 1)
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((then.getTime() - today.getTime()) / 86400000)
}

export type DatedMeeting = { date: string }

/** A board's meetings, split by the reader's clock.
 *
 *  A MEETING ON TODAY'S DATE COUNTS AS UPCOMING until the day is over. It usually has not
 *  happened yet when somebody looks in the morning, and a meeting that vanishes from
 *  "upcoming" at midnight on the day it is held is the bug this module exists to prevent,
 *  one day earlier.
 *
 *  `upcoming` is soonest first, because the next one is the one a reader came for.
 *  `past` is newest first, for the same reason. */
export function splitMeetings<T extends DatedMeeting>(
  meetings: T[] | undefined | null, now: Date = new Date(),
): { upcoming: T[]; past: T[] } {
  const today = todayIso(now)
  const all = meetings ?? []
  return {
    upcoming: all.filter(m => m.date >= today).slice().sort((a, b) => a.date.localeCompare(b.date)),
    past: all.filter(m => m.date < today).slice().sort((a, b) => b.date.localeCompare(a.date)),
  }
}

/** `Today · Tue Sep 15`, `Tomorrow · ...`, or the plain date.
 *
 *  TJ, September 2026: *"I see 'tomorrow' for something that is very much today (and we
 *  always need to show the day of the week and the date)."* The payload carries the day it
 *  was BUILT; a page read two days later must not call that day "today". So the comparison
 *  is the browser's clock and the weekday is always shown -- never a bare "Tomorrow".
 *
 *  `_asOf` is accepted and ignored on purpose: callers used to pass the payload's build date
 *  and that is exactly the value this must not use. Taking it and dropping it keeps those
 *  call sites honest without making them all change at once. */
export function dayLabel(iso: string, _asOf?: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, (m || 1) - 1, d || 1)
  const diff = daysAway(iso)
  const full = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  if (diff === 0) return `Today \u00b7 ${full}`
  if (diff === 1) return `Tomorrow \u00b7 ${full}`
  return full
}

/** `in 3 days`, `tomorrow`, `today`, or how long ago it was. */
export function whenPhrase(date: string, now: Date = new Date()): string {
  const n = daysAway(date, now)
  if (n === 0) return 'today'
  if (n === 1) return 'tomorrow'
  if (n === -1) return 'yesterday'
  if (n > 1) return `in ${n} days`
  return `${-n} days ago`
}


/** What to call the body that is actually meeting.
 *
 *  TJ, 25 September 2026: *"Quick major bug. School committee shows a meeting for today
 *  which is wrong."* There was a meeting; its agenda read `SCHOOL COMMITTEE POLICY
 *  SUB-COMMITTEE` and three people attended. The town files those under its School
 *  Committee category, so the front page announced one of the three budget boards.
 *
 *  THE DOCUMENT OUTRANKS THE FOLDER. Where the agenda names a sub-committee of the board it
 *  is filed under, that printed name is what a reader is shown -- title-cased, because the
 *  notices are typed in full capitals and a shouted line in a list of meetings reads as an
 *  error rather than as emphasis. The board's own name stays available as `board` for the
 *  link and the grouping; only the label changes.
 */
export function meetingBody(board: string, printed?: string | null): string {
  if (!printed) return board
  const t = printed.trim()
  const shouty = t === t.toUpperCase()
  if (!shouty) return t
  return t.toLowerCase().replace(/\b([a-z])/g, (_m, c: string) => c.toUpperCase())
}
