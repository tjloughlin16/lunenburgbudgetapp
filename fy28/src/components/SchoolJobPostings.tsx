import { Grain, H3, Section, Stat, useReport } from './report'

/** THE DISTRICT'S JOB OPENINGS, open now and as a history. On the School Committee page.
 *
 *  TJ, 5 October 2026: "on the school committee page we need to list the history of the
 *  openings, including the active postings. But the history can be when something was
 *  posted, removed. If we get the details too like salary and description we can show the
 *  changes made per date."
 *
 *  MODEL-DRIVEN (rule 7d). Everything here is `/data/school-job-postings.json`, written by
 *  scripts/extract_school_job_postings.py in the same pass as the two CSVs it publishes --
 *  this file formats and lays out, it computes nothing.
 *
 *  RULE 7, BESIDE THE THING IT QUALIFIES (rule 7a): a history date is the day OUR daily
 *  check saw the change, not the day the district made it; `removed` means the posting
 *  came down, not that anybody was hired; and a posting is not a vacancy count. Each of
 *  those is one line next to the list it is about, not a preface above everything. */

type Active = {
  id: string; title: string; school: string; posted: string; displayed: string
  closes: string; pay: string; positions: string; job_type: string
  api_url: string; page_url: string; first_seen: string
}
type Line = { op: '-' | '+'; text: string }
type Event = {
  date: string; prev_look: string; id: string
  event: 'posted' | 'edited' | 'removed' | 'relisted'
  title: string; school: string; posted: string; source: string; api_url: string
  field?: string; before?: string; after?: string; diff?: Line[]
}
type Payload = {
  as_of: string; tracking_since: string; tracking_since_text: string; looks: number
  stats: { value: string; label: string }[]
  grain: string
  active: Active[]
  history: Event[]
  sources: { label: string; url: string }[]
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function d(iso: string) {
  if (!iso) return ''
  const [y, m, dd] = iso.split('-').map(Number)
  return `${dd} ${MONTHS[m - 1]} ${y}`
}

/** A field value as the page prints it: an ISO date reads as a date, anything else as is. */
function v(x?: string) {
  if (!x) return '(blank)'
  return /^\d{4}-\d{2}-\d{2}$/.test(x) ? d(x) : x
}

const TONE: Record<Event['event'], string> = {
  posted: 'var(--status-good)',
  relisted: 'var(--status-good)',
  edited: 'var(--status-warning)',
  removed: 'var(--status-critical)',
}

export function SchoolJobPostings() {
  const { d: p } = useReport<Payload>('school-job-postings.json')
  if (!p) return null
  const days = Array.from(new Set(p.history.map(h => h.date)))
  return (
    <Section kind="categorical" id="jobs" title="Job openings">
      <p className="text-[15px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
        What the district has advertised on SchoolSpring, open now and since we began
        checking on {p.tracking_since_text}.
      </p>

      {/* --------------------------------------------------------------- open now */}
      <H3>Open now: {p.active.length} posting{p.active.length === 1 ? '' : 's'}, at our check of {d(p.as_of)}</H3>
      <div className="grid gap-3 mt-3 sm:grid-cols-2 max-w-3xl">
        {p.active.map(a => (
          <div key={a.id} className="card p-4 avoid-break min-w-0">
            <p className="text-[14.5px] font-bold leading-snug break-words">{a.title}</p>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
              {a.school}{a.job_type ? ` · ${a.job_type}` : ''}
              {a.positions && a.positions !== '1' ? ` · ${a.positions} positions listed` : ''}
            </p>
            <p className="text-[12.5px] mt-2 tnum">
              Posted {d(a.posted)}{a.displayed ? <span style={{ color: 'var(--text-muted)' }}> (re-dated {d(a.displayed)})</span> : null}
              {a.closes ? <> · closes {d(a.closes)}</> : null}
            </p>
            {a.pay && <p className="text-[12.5px] mt-1 tnum"><strong>{a.pay}</strong></p>}
            <p className="text-[11.5px] mt-2 break-words" style={{ color: 'var(--text-muted)' }}>
              <a className="underline" href={a.api_url}>source: SchoolSpring</a>
              {' · '}
              <a className="underline" href={a.page_url} rel="noreferrer">job page</a> (address not verified)
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Dates are SchoolSpring&rsquo;s. Pay is shown only where SchoolSpring shows it. A posting
        is one advertisement, not one vacancy.
      </p>

      {/* ---------------------------------------------------------------- history */}
      <H3>The history, newest first</H3>
      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-4">
        {p.stats.map(s => <Stat key={s.label} value={s.value}>{s.label}</Stat>)}
      </div>
      <p className="text-xs mt-4 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        A date below is the day our daily check <em>saw</em> the change; the district made it
        some time after the check before. &ldquo;Taken down&rdquo; means the posting stopped
        being listed &mdash; filled, closed, withdrawn or reposted; nothing here says which.
      </p>
      <div className="mt-3 max-w-3xl">
        {days.map(day => {
          const ev = p.history.filter(h => h.date === day)
          const first = day === p.tracking_since
          return (
            <div key={day} className="mt-5">
              <p className="text-[13px] font-bold tnum">
                {d(day)}
                <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
                  {first
                    ? ` · tracking began: ${ev.length} posting${ev.length === 1 ? '' : 's'} already listed`
                    : ev[0]?.prev_look ? ` · changed since our check of ${d(ev[0].prev_look)}` : ''}
                </span>
              </p>
              <ul className="mt-1.5">
                {ev.map((e, i) => <EventLine key={`${e.id}-${e.event}-${e.field ?? ''}-${i}`} e={e} first={first} />)}
              </ul>
            </div>
          )
        })}
      </div>

      <Grain>{p.grain}</Grain>
      <p className="text-xs mt-3 max-w-2xl break-words" style={{ color: 'var(--text-muted)' }}>
        Sources: {p.sources.map((s, i) => (
          <span key={s.url}>{i ? ' · ' : ''}<a className="underline" href={s.url}>{s.label}</a></span>
        ))}. Checked {p.looks} time{p.looks === 1 ? '' : 's'} so far.
      </p>
    </Section>
  )
}

function EventLine({ e, first }: { e: Event; first: boolean }) {
  const word = e.event === 'posted' ? (first ? 'listed' : 'posted')
    : e.event === 'removed' ? 'taken down' : e.event === 'relisted' ? 'listed again' : 'edited'
  return (
    <li className="py-1.5 text-[13.5px] min-w-0" style={{ borderTop: '1px solid var(--grid)' }}>
      <span className="text-[10.5px] font-bold uppercase tracking-wider mr-2"
        style={{ color: TONE[e.event] }}>{word}</span>
      <span className="font-semibold break-words">{e.title}</span>
      <span style={{ color: 'var(--text-muted)' }}> · {e.school}</span>
      {e.event === 'posted' && e.posted && (
        <span className="tnum" style={{ color: 'var(--text-muted)' }}> · SchoolSpring post date {d(e.posted)}</span>
      )}
      {e.event === 'removed' && e.prev_look && (
        <span style={{ color: 'var(--text-muted)' }}> · last listed at our check of {d(e.prev_look)}</span>
      )}
      {e.event === 'edited' && !e.diff && (
        <span className="block text-[13px] mt-0.5 break-words">
          <span style={{ color: 'var(--text-muted)' }}>{e.field}: </span>
          <span style={{ textDecoration: 'line-through', color: 'var(--text-muted)' }}>{v(e.before)}</span>
          {' → '}<strong>{v(e.after)}</strong>
        </span>
      )}
      {e.event === 'edited' && e.diff && (
        <details className="mt-0.5">
          <summary className="cursor-pointer text-[13px]" style={{ color: 'var(--text-secondary)' }}>
            {e.field} changed: {e.diff.filter(l => l.op === '-').length} line{e.diff.filter(l => l.op === '-').length === 1 ? '' : 's'} out, {e.diff.filter(l => l.op === '+').length} in
          </summary>
          <div className="mt-1.5 text-[12.5px] leading-relaxed">
            {e.diff.map((l, i) => (
              <p key={i} className="break-words px-2 py-0.5"
                style={{
                  background: l.op === '+' ? 'var(--surface-3)' : undefined,
                  color: l.op === '-' ? 'var(--text-muted)' : undefined,
                  textDecoration: l.op === '-' ? 'line-through' : undefined,
                }}>
                <span aria-hidden className="mr-1">{l.op === '+' ? '+' : '−'}</span>{l.text}
              </p>
            ))}
          </div>
        </details>
      )}
      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {' '}· <a className="underline" href={e.api_url}>source</a> · <a className="underline" href={e.source}>our copy</a>
      </span>
    </li>
  )
}
