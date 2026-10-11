import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Grain, H3, ReportShell, Section, useReport } from './report'

/** JOB POSTINGS -- THE TOWN'S AND THE SCHOOL DISTRICT'S, open now and as a history.
 *
 *  TJ, 10 October 2026: *"make sure the boards and department pages have a JOB POSTINGS page
 *  linked for any jobs available. And a history on that same page of openings and fills."*
 *  The district's postings used to live as a section of the School Committee page, which
 *  left nowhere for the town's to go and nothing for a department page to link to. So the
 *  postings are one page, `/jobs`, and every board or department page that owns a posting
 *  carries a link to its part of it (`JobsLink`).
 *
 *  MODEL-DRIVEN (rule 7d). Everything is `/data/job-postings.json`, written by
 *  scripts/build_job_postings.py in the same pass as the town's two tables; this file lays
 *  out, it computes nothing. Which board or department a posting belongs to is decided there,
 *  from `job-posting-owners.csv`, with its basis -- ours, and said so on the page.
 *
 *  TAKEN DOWN, NEVER FILLED (rule 7). Asked for as "fills"; what either site shows is only
 *  that a posting stopped being listed. Filled is one cause among several, and nothing either
 *  employer publishes says which, so every label here says taken down. */

type Employer = {
  id: 'town' | 'schools'; name: string; where: string; url: string
  tracking_since: string; tracking_since_text: string; as_of: string; looks: number
  open: number; seen: number; taken_down: number
}
type Active = {
  employer: Employer['id']; id: string; title: string; department: string
  posted: string; closes: string; closing_as_printed: string; job_type: string
  positions: string; url: string; source: string; first_seen: string; owner: string
}
type Event = {
  employer: Employer['id']; date: string; prev_look: string; id: string
  event: 'posted' | 'edited' | 'removed' | 'relisted'
  title: string; posted: string; owner: string; source: string
  field?: string; before?: string; after?: string
}
type Owner = { name: string; href: string; kind: string; basis: string; open: number; seen: number }
type Payload = {
  as_of: string; as_of_text: string
  employers: Employer[]
  owners: Record<string, Owner>
  active: Active[]
  history: Event[]
  unmatched: string[]
  grain: string
  sources: { label: string; url: string }[]
}

const FILE = 'job-postings.json'
export const JOBS_PAGE = '/jobs'
/** One posting's place on /jobs: its card while open, its `taken down` line after. */
export const jobAnchor = (employer: string, id: string, down: boolean) =>
  `job-${employer}-${id}${down ? '-down' : ''}`

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function d(iso: string) {
  if (!iso) return ''
  const [y, m, dd] = iso.split('-').map(Number)
  return `${dd} ${MONTHS[m - 1]} ${y}`
}
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
const WORD: Record<Event['event'], string> = {
  posted: 'posted', relisted: 'listed again', edited: 'edited', removed: 'taken down',
}

/* ------------------------------------------------------------------------- the page */

export function JobsPage() {
  const { d: p, err } = useReport<Payload>(FILE)
  // THE CARDS ARRIVE AFTER THE BROWSER HAS ALREADY LOOKED FOR THE ANCHOR, and the sections
  // above a card keep arriving after that and push it down (layout shift) -- measured, one
  // scroll left the reader somewhere else. So go to the named posting, and again as the page
  // settles, until the reader scrolls for themselves.
  useEffect(() => {
    if (!p || !window.location.hash.startsWith('#job')) return
    const el = () => document.getElementById(window.location.hash.slice(1))
    let stopped = false
    const stop = () => { stopped = true }
    window.addEventListener('wheel', stop, { once: true })
    window.addEventListener('touchmove', stop, { once: true })
    const timers = [0, 400, 1000, 2000].map(ms => window.setTimeout(() => {
      if (!stopped) el()?.scrollIntoView({ block: 'center' })
    }, ms))
    return () => {
      timers.forEach(clearTimeout)
      window.removeEventListener('wheel', stop)
      window.removeEventListener('touchmove', stop)
    }
  }, [p])
  const open = p?.active.length ?? 0
  return (
    <ReportShell tab="jobs" title="Job postings" err={err} loading={!p && !err}
      dataUrl={`/data/${FILE}`}
      standfirst={p
        ? <>{open} open posting{open === 1 ? '' : 's'} from the town and the school district at our check of {p.as_of_text}, and every one we have seen come and go.</>
        : 'Open jobs at the town and the school district, and every posting we have seen come and go.'}>
      {p && <>
        {p.employers.map(e => <EmployerSection key={e.id} e={e} p={p} />)}
        <Section kind="raw" id="jobs-about" title="What this counts">
          <Grain>{p.grain}</Grain>
          <p className="text-xs mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Each posting is linked from the page of the board or department it belongs to.
            That link is ours, not the employer&rsquo;s: {Object.values(p.owners).map((o, i, a) => (
              <span key={o.href}>{i ? (i === a.length - 1 ? ' and ' : '; ') : ''}<a className="underline" href={o.href}>{o.name}</a> ({o.basis.replace(/^ours: /, '')})</span>
            ))}.
            {p.unmatched.length > 0 && <> {p.unmatched.length} posting{p.unmatched.length === 1 ? ' is' : 's are'} linked from no page yet: {p.unmatched.join('; ')}.</>}
          </p>
          <p className="text-xs mt-3 max-w-2xl break-words" style={{ color: 'var(--text-muted)' }}>
            Sources: {p.sources.map((s, i) => (
              <span key={s.url}>{i ? ' · ' : ''}<a className="underline" href={s.url}>{s.label}</a></span>
            ))}.
          </p>
        </Section>
      </>}
    </ReportShell>
  )
}

function EmployerSection({ e, p }: { e: Employer; p: Payload }) {
  const active = p.active.filter(a => a.employer === e.id)
  const history = p.history.filter(h => h.employer === e.id)
  const days = Array.from(new Set(history.map(h => h.date)))
  return (
    <Section kind="categorical" id={`jobs-${e.id}`} title={e.name}>
      <p className="text-[14px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
        As listed on <a className="underline" href={e.url} target="_blank" rel="noreferrer">{e.where}</a>, checked daily since {e.tracking_since_text}.
      </p>

      <H3>Open now: {active.length} posting{active.length === 1 ? '' : 's'}</H3>
      {active.length === 0
        ? <p className="text-[14px] mt-2" style={{ color: 'var(--text-muted)' }}>Nothing listed at our check of {d(e.as_of)}.</p>
        : <div className="grid gap-3 mt-3 sm:grid-cols-2 max-w-3xl">
          {active.map(a => {
            const o = p.owners[a.owner]
            return (
              <div key={a.id} id={jobAnchor(a.employer, a.id, false)}
                className="card p-4 avoid-break min-w-0 scroll-mt-24 target:ring-2 target:ring-[var(--status-good)]">
                <a className="text-[14.5px] font-bold leading-snug break-words underline" href={a.url}
                  target="_blank" rel="noreferrer" style={{ color: 'var(--series-cost)' }}>{a.title}</a>
                <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                  {[a.department, a.job_type, a.positions && a.positions !== '1' ? `${a.positions} positions listed` : ''].filter(Boolean).join(' · ')}
                </p>
                <p className="text-[12.5px] mt-2 tnum">
                  Posted {d(a.posted)}
                  {a.closes ? <> · closes {d(a.closes)}</> : a.closing_as_printed ? <> · {a.closing_as_printed.toLowerCase()}</> : null}
                </p>
                <p className="text-[11.5px] mt-2 break-words" style={{ color: 'var(--text-muted)' }}>
                  {o && <><a className="underline" href={o.href}>{o.name}</a> · </>}
                  <a className="underline" href={a.source}>our copy</a>
                </p>
              </div>
            )
          })}
        </div>}

      <H3>The history, newest first</H3>
      <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {e.seen} posting{e.seen === 1 ? '' : 's'} seen since {e.tracking_since_text}; {e.taken_down} taken down.
        A date is the day our check <em>saw</em> the change. &ldquo;Taken down&rdquo; means a posting
        stopped being listed &mdash; filled, closed, withdrawn or reposted; neither site says which.
      </p>
      <div className="mt-2 max-w-3xl">
        {days.map(day => {
          const ev = history.filter(h => h.date === day)
          const first = !ev[0]?.prev_look
          return (
            <div key={day} className="mt-4">
              <p className="text-[13px] font-bold tnum">
                {d(day)}
                <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
                  {first ? ` · tracking began: ${ev.length} already listed`
                    : ` · changed since our check of ${d(ev[0].prev_look)}`}
                </span>
              </p>
              <ul className="mt-1">
                {ev.map((h, i) => <EventLine key={`${h.id}-${h.event}-${h.field ?? ''}-${i}`} h={h} first={first} />)}
              </ul>
            </div>
          )
        })}
      </div>
    </Section>
  )
}

function EventLine({ h, first }: { h: Event; first: boolean }) {
  const word = h.event === 'posted' && first ? 'listed' : WORD[h.event]
  return (
    <li id={h.event === 'removed' ? jobAnchor(h.employer, h.id, true) : undefined}
      className="py-1.5 text-[13.5px] min-w-0 scroll-mt-24 target:bg-[var(--surface-3)]"
      style={{ borderTop: '1px solid var(--grid)' }}>
      <span className="text-[10.5px] font-bold uppercase tracking-wider mr-2" style={{ color: TONE[h.event] }}>{word}</span>
      <span className="font-semibold break-words">{h.title}</span>
      {h.event === 'posted' && h.posted && (
        <span className="tnum" style={{ color: 'var(--text-muted)' }}> · post date {d(h.posted)}</span>
      )}
      {h.event === 'removed' && h.prev_look && (
        <span style={{ color: 'var(--text-muted)' }}> · last listed at our check of {d(h.prev_look)}</span>
      )}
      {h.event === 'edited' && (
        <span className="block text-[13px] mt-0.5 break-words">
          <span style={{ color: 'var(--text-muted)' }}>{h.field}{h.before === undefined ? ' changed' : ': '}</span>
          {h.before !== undefined && <>
            <span style={{ textDecoration: 'line-through', color: 'var(--text-muted)' }}>{v(h.before)}</span>
            {' → '}<strong>{v(h.after)}</strong>
          </>}
        </span>
      )}
      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {' '}· <a className="underline" href={h.source}>our copy</a>
      </span>
    </li>
  )
}

/* ------------------------------------------- the link on a board or department page */

/** JOB POSTINGS, ON THE PAGE OF THE BODY THAT OWNS THEM. Renders only for a body with a
 *  posting open or seen; a body that never posted gets nothing, not an empty box. */
export function JobsLink({ slug }: { slug: string }) {
  const { d: p } = useReport<Payload>(FILE)
  const o = p?.owners[slug]
  if (!p || !o || (o.open === 0 && o.seen === 0)) return null
  const open = p.active.filter(a => a.owner === slug)
  const down = p.history.filter(h => h.owner === slug && h.event === 'removed').length
  const emp = p.employers.find(e => open[0] ? e.id === open[0].employer : p.history.some(h => h.owner === slug && h.employer === e.id))
  const where = emp ? `${JOBS_PAGE}#jobs-${emp.id}` : JOBS_PAGE
  return (
    <section id="jobs" aria-label="Job postings" className="card p-4 mt-6 max-w-3xl scroll-mt-24">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Job postings</h2>
        <a className="text-[13px] font-semibold underline" href={where} style={{ color: 'var(--series-cost)' }}>
          {open.length ? `${open.length} open` : 'none open'}{down ? ` · ${down} taken down` : ''} — openings and history &rarr;
        </a>
      </div>
      {open.length > 0 && (
        <ul className="mt-2 space-y-1">
          {open.slice(0, 4).map(a => (
            <li key={a.id} className="text-[13.5px] min-w-0 truncate">
              <a className="underline" href={`${JOBS_PAGE}#${jobAnchor(a.employer, a.id, false)}`}>{a.title}</a>
              <span className="tnum" style={{ color: 'var(--text-muted)' }}> · posted {d(a.posted)}</span>
            </li>
          ))}
          {open.length > 4 && <li className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>and {open.length - 4} more</li>}
        </ul>
      )}
    </section>
  )
}

/* ------------------------------------------------- the slide-out, top right, every page */

/** NEW JOB POSTED / JOB TAKEN DOWN, AS A NOTIFICATION. TJ, 10 October 2026: *"I also want a
 *  NEW JOB POSTED notification like thing on the main page when we detect a new job,
 *  clickable to details. And JOB FILLED when it's taken down."* -- and then, on seeing it as a
 *  strip of cards under the front page's title: *"the job posting 'notifications' are NOT
 *  notifications.... you built it as a top section"* and *"it should probably be a tab on the
 *  top right that can slide out"*.
 *
 *  So it is a NOTIFICATION TRAY: a button in the header on every page, a badge only for what
 *  arrived since the reader last opened it, and a panel that slides in from the right over
 *  the page instead of pushing the page down. The page underneath does not move -- which is
 *  the difference between a notification and a section.
 *
 *  THE PANEL IS PORTALLED TO <body>. The header scrolls sideways on a phone (overflow-x) and
 *  carries a backdrop blur, and either would clip or re-anchor a fixed panel drawn inside it:
 *  `backdrop-filter` makes an element the containing block for its fixed descendants.
 *
 *  "SEEN" LIVES IN THIS BROWSER ONLY, and its absence is harmless: with no record every event
 *  in the window counts as new, which is what a first visit should show. A private window or
 *  blocked storage gets that, never an error.
 *
 *  IT SAYS TAKEN DOWN, NOT FILLED -- see the header of this file. And ONLY WHAT WE DETECTED:
 *  postings already listed on an employer's first check have no `prev_look` and are left out.
 *  The window counts from the reader's today, so a page nobody redeployed does not keep
 *  calling a fortnight-old posting new. */
const WINDOW_DAYS = 14
const SEEN_KEY = 'jobs-seen-through'

function readSeen(): string {
  try { return window.localStorage.getItem(SEEN_KEY) || '' } catch { return '' }
}
function writeSeen(iso: string) {
  try { window.localStorage.setItem(SEEN_KEY, iso) } catch { /* private window: harmless */ }
}

export function JobsTray() {
  const { d: p } = useReport<Payload>(FILE)
  const [open, setOpen] = useState(false)
  const [seen, setSeen] = useState('')
  // What counted as seen WHEN THE PANEL OPENED: opening marks everything seen, and reading
  // `seen` after that would strip the "new to you" marker off the very items it is for.
  const [seenAtOpen, setSeenAtOpen] = useState('')
  useEffect(() => { setSeen(readSeen()) }, [])
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [open])
  const since = new Date(Date.now() - WINDOW_DAYS * 864e5).toISOString().slice(0, 10)
  const news = (p?.history ?? []).filter(e => e.date >= since && e.prev_look
    && (e.event === 'removed' || e.event === 'posted' || e.event === 'relisted'))
  const unseen = news.filter(e => !seen || e.date > seen).length
  const openTray = () => {
    setSeenAtOpen(seen)
    setOpen(true)
    const latest = news[0]?.date || ''
    if (latest) { writeSeen(latest); setSeen(latest) }
  }
  const live = new Set((p?.active ?? []).map(a => `${a.employer}:${a.id}`))
  const who = (e: Event) => e.employer === 'town' ? 'Town' : 'Schools'
  return (
    <>
      <button type="button" onClick={openTray} aria-haspopup="dialog" aria-expanded={open}
        title="Job postings: what is new"
        aria-label={unseen ? `Jobs, ${unseen} new` : 'Jobs'}
        className="relative inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded whitespace-nowrap shrink-0"
        style={{ color: 'var(--text-secondary)' }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
        <span className="hidden sm:inline">Jobs</span>
        {unseen > 0 && (
          <span className="tnum text-[10px] leading-none font-bold rounded-full px-1.5 py-0.5"
            style={{ background: 'var(--status-good)', color: '#fff' }}>{unseen}</span>
        )}
      </button>
      {open && createPortal(
        <div className="fixed inset-0 z-50 no-print" role="dialog" aria-modal="true" aria-label="Job postings: what is new">
          <button type="button" aria-label="Close" onClick={() => setOpen(false)}
            className="absolute inset-0 w-full h-full cursor-default" style={{ background: 'rgba(0,0,0,0.25)' }} />
          <aside className="absolute right-0 top-0 h-full w-[min(24rem,100vw)] overflow-y-auto shadow-xl p-4 jobs-tray-in"
            style={{ background: 'var(--surface-1)', borderLeft: '1px solid var(--grid)' }}>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Job postings</h2>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close"
                className="text-xl leading-none px-2" style={{ color: 'var(--text-secondary)' }}>&times;</button>
            </div>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
              {p ? `${p.active.length} open at the town and the schools. ` : ''}What changed in the last {WINDOW_DAYS} days:
            </p>
            {news.length === 0
              ? <p className="text-[13.5px] mt-4" style={{ color: 'var(--text-muted)' }}>Nothing posted or taken down in that time.</p>
              : <ul className="mt-3 space-y-1.5">
                {news.map((e, i) => {
                  const down = e.event === 'removed'
                  const href = `${JOBS_PAGE}#${jobAnchor(e.employer, e.id, down || !live.has(`${e.employer}:${e.id}`))}`
                  return (
                    <li key={`${e.employer}-${e.id}-${e.event}-${i}`}>
                      <a href={href} onClick={() => setOpen(false)}
                        className="block card px-3 py-2 no-underline hover:underline min-w-0"
                        style={{ borderLeft: `4px solid ${TONE[e.event]}` }}>
                        <span className="flex items-baseline justify-between gap-2">
                          <span className="text-[10.5px] font-bold uppercase tracking-wider" style={{ color: TONE[e.event] }}>
                            {down ? 'Taken down' : e.event === 'relisted' ? 'Listed again' : 'New'}
                            {(!seenAtOpen || e.date > seenAtOpen) && <span className="ml-1.5 normal-case tracking-normal font-semibold" style={{ color: 'var(--text-muted)' }}>· new to you</span>}
                          </span>
                          <span className="text-[11px] tnum shrink-0" style={{ color: 'var(--text-muted)' }}>{who(e)} · {d(e.date)}</span>
                        </span>
                        <span className="block text-[13.5px] font-semibold mt-0.5 break-words">{e.title}</span>
                      </a>
                    </li>
                  )
                })}
              </ul>}
            <p className="text-[11.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
              Checked daily. Taken down is not the same as filled &mdash; neither site says why a posting came down.
            </p>
            <a href={JOBS_PAGE} onClick={() => setOpen(false)} className="inline-block mt-3 text-[13px] font-semibold underline"
              style={{ color: 'var(--series-cost)' }}>Every opening, and the full history &rarr;</a>
          </aside>
        </div>,
        document.body,
      )}
    </>
  )
}
