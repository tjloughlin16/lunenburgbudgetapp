import { useEffect } from 'react'
import type { Tab } from '../routes'
import { omlSlugFromPath } from '../routes'
import { ReportShell, useReport, H2, Body } from '../components/report'

const TAB: Tab = 'recorded'

/** OPEN MEETING LAW: POINTS TO CHECK, for one meeting. EXPERIMENTAL AND UNLISTED.
 *
 *  Rendered from `/data/oml/<board>/<date>-<video>.json`, written by
 *  scripts/oml_review.py. Every point carries the rule, quoted from the law as the State
 *  publishes it, beside the evidence, quoted from the agenda, the town's minutes or the
 *  machine captions -- each quotation checked verbatim by the script, and a point whose
 *  quotes were not is dropped before it reaches this page.
 *
 *  HIDDEN, and the four doors are shut on purpose: nothing links here; it is not in the
 *  sitemap (build_sitemap.py enumerates /meeting-minutes/<slug> from the minutes payload,
 *  never this suffix); it is not prerendered (prerender.mjs does the same); and it is
 *  noindex twice -- the robots meta below and an X-Robots-Tag in public/_headers.
 *
 *  The page never says a board broke the law. Only the Attorney General's office decides
 *  that, and the disclaimer leads because it changes how everything under it is read
 *  (rule 7a's one exception). */

type Evidence = { source: 'agenda' | 'minutes' | 'captions' | 'file metadata'; quote: string; t?: number; url?: string; text_url?: string; note?: string }
type Rule = { doc: string; section: string; quote: string; label: string; upstream: string; our_copy: string }
/** An AG determination the point cites -- how the Attorney General read the rule for ANOTHER
 *  body on its own facts. `holding` belongs to the quoted passage, not the whole letter: one
 *  letter decides many allegations (OML 2013-195 holds 26 times, both ways). Blank when the
 *  quoted words are not one of the digest's key passages; the page then says to read it. */
type Precedent = {
  id: string; quote: string; number: string; public_body: string; holding: string
  label: string; upstream: string; our_copy: string; note: string
}
/** THE SECOND PASS (scripts/oml_deepen.py): an agent with read-only search over every AG letter
 *  and the town's documents researched a point the one-call review flagged. Its quotes are
 *  checked verbatim like the first pass's; a discarded or failed pass is not shown. */
type Deepened = {
  outcome: string; status_before: string; summary: string; question: string; note: string
  precedent: Precedent[]; evidence: { path: string; quote: string; t?: number; url?: string }[]
}
type Finding = {
  criterion: string; title: string; status: string; bearing: string; summary: string
  rule: Rule; evidence: Evidence[]; settle: string; by: 'model' | 'script'
  precedent?: Precedent[]
  deepened?: Deepened
}
/** The one or two points with the most AG precedent behind them, picked by a model-free score
 *  in scripts/oml_review.py (standout). The score is deliberately NOT shown: TJ, 13 November
 *  2026 -- the page shows the facts the score rests on, never a number of ours. */
type Standout = {
  finding: number; title: string; issue: string; strength: string; status: string
  record: { ruled_against: number; ruled_for: number; against_school_committees: number }
  rule_written_in: string; cited_against: string[]
}
type AgendaVersion = {
  version: number; file_id: string; title: string; url: string; text_url: string; created: string
  operative: boolean; counted_hours_file_to_meeting: number | null
  removed_in_next?: string[]; added_in_next?: string[]
}
type Review = {
  title: string; disclaimer: string; board: string; board_slug: string; date: string
  video_url: string; agenda_url: string; minutes_url: string; our_minutes_page: string
  agenda_text_url?: string; minutes_text_url?: string
  inputs?: Record<string, { path: string; sha256: string }>
  stage?: string; waiting_for?: string[]
  history?: { stage: string; at: string; points: number }[]
  agenda_versions?: AgendaVersion[]
  overall: string; counts: Record<string, number>; findings: Finding[]; standout?: Standout[]
  dropped: { title: string; why: string }[]; cannot_see: string[]; statuses: Record<string, string>
  written: { model: string; at: string; cost_usd: number }
}

const STRENGTH_COLOR: Record<string, string> = {
  'well settled': 'var(--series-revenue, #b5540f)',
  'often ruled on': 'var(--series-revenue, #b5540f)',
  'some precedent': 'var(--text-muted)',
  'little precedent': 'var(--text-muted)',
}

const n0 = (x: number) => x.toLocaleString('en-US')
const SITE = 'https://lunenburgbudgetproject.org'

/** WHAT STANDS OUT: after the metrics, before the points. Each item says what the record shows
 *  (the point's own summary) and how much precedent stands behind that kind of point -- how
 *  often the Attorney General has ruled against a board on the issue, and where the rule is
 *  written. Never the word the law uses for a breach: only the AG decides that. */
function StandoutBlock({ items, findings, order }: { items: Standout[]; findings: Finding[]; order: number[] }) {
  return (
    <div className="mt-6 rounded-lg border-2 p-4 sm:p-5" style={{ borderColor: 'var(--series-revenue, #b5540f)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--series-revenue, #b5540f)' }}>
        what stands out
      </p>
      {items.length === 0 && (
        <p className="mt-2 text-[15px]" style={{ color: 'var(--text-secondary)' }}>
          Nothing on this record matches the kinds of point the Attorney General most often rules against a board on.
        </p>
      )}
      {items.map((x, i) => {
        const f = findings[x.finding]
        const n = order.indexOf(x.finding) + 1
        const r = x.record
        return (
          <div key={i} className={i ? 'mt-5 pt-4 border-t' : 'mt-2'} style={{ borderColor: 'var(--grid)' }}>
            <div className="flex flex-wrap items-center gap-2">
              <a href={`#point-${n}`} className="text-[18px] font-bold leading-snug underline-offset-2" style={{ color: 'var(--text-primary)' }}>
                {x.title}
              </a>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider"
                style={{ border: `1px solid ${STRENGTH_COLOR[x.strength]}`, color: STRENGTH_COLOR[x.strength] }}>
                {x.strength}
              </span>
            </div>
            <p className="mt-1 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{f?.summary}</p>
            <p className="mt-2 text-[13px] leading-relaxed">
              <span className="font-semibold">The Attorney General has ruled against a board on this
              ({x.issue}) in {n0(r.ruled_against)} letters</span>, and for the board in {n0(r.ruled_for)}
              {r.against_school_committees ? <>; {n0(r.against_school_committees)} of those rulings were against school committees</> : null}.
              {' '}The rule is in {x.rule_written_in}.
              {x.cited_against.length > 0 && <> Cited here: {x.cited_against.join(', ')}, ruled against that board.</>}
              {' '}<a className="underline" href={`#point-${n}`}>Point {n}</a> &middot; {x.status}
            </p>
          </div>
        )
      })}
    </div>
  )
}

/** THE RECORD, before anything else is read. TJ, 13 November 2026: "near the top we need the
 *  relevant docs (minutes, transcript) listed so i can easily click to see the context". */
function RecordLinks({ d }: { d: Review }) {
  const tp = d.inputs?.transcript?.path
  const transcript = tp ? `${SITE}/docs/${tp.replace(/^sources\//, '')}` : ''
  const row: { label: string; links: { text: string; href: string }[]; missing?: string }[] = [
    { label: 'Agenda', links: [{ text: 'as posted', href: d.agenda_url },
      ...(d.agenda_text_url ? [{ text: 'text', href: d.agenda_text_url }] : [])] },
    d.minutes_url
      ? { label: 'Official minutes', links: [{ text: 'as posted', href: d.minutes_url },
          ...(d.minutes_text_url ? [{ text: 'text', href: d.minutes_text_url }] : [])] }
      : { label: 'Official minutes', links: [], missing: 'not yet posted' },
    d.video_url
      ? { label: 'Recording', links: [{ text: 'video', href: d.video_url }] }
      : { label: 'Recording', links: [], missing: 'none held yet' },
    { label: 'Transcript', links: transcript ? [{ text: 'machine captions', href: transcript }] : [],
      missing: transcript ? undefined : 'none held' },
    ...(d.our_minutes_page ? [{ label: 'Our minutes', links: [{ text: 'of the recording', href: d.our_minutes_page }] }] : []),
  ]
  return (
    <div className="mt-5 flex flex-wrap gap-2">
      {row.map(r => (
        <div key={r.label} className="rounded-md border px-3 py-2 text-[13px]" style={{ borderColor: 'var(--grid)' }}>
          <span className="font-semibold">{r.label}</span>
          {r.links.map(l => (
            <span key={l.text}> &middot; <a className="underline" href={l.href} target="_blank" rel="noreferrer"
              style={{ color: 'var(--series-cost)' }}>{l.text}</a></span>
          ))}
          {r.missing && <span style={{ color: 'var(--text-muted)' }}> &middot; {r.missing}</span>}
        </div>
      ))}
    </div>
  )
}

function postedAt(iso: string) {
  if (!iso) return 'time not recorded'
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

/** WHAT THIS REVIEW COULD READ. One review per meeting, redone as the record grows: agenda only,
 *  then the recording, then the official minutes (TJ, 13 November 2026). */
function StageNote({ d }: { d: Review }) {
  if (!d.waiting_for || d.waiting_for.length === 0) return null
  return (
    <p className="mt-3 rounded-md px-3 py-2 text-[14px]" style={{ background: 'var(--surface-2, rgba(127,127,127,0.08))' }}>
      <span className="font-semibold">Reviewed from the {d.stage}.</span>{' '}
      Still waiting for {d.waiting_for.join(' and ')}; this review will be redone when {d.waiting_for.length > 1 ? 'they are' : 'it is'} posted,
      and anything only {d.waiting_for.length > 1 ? 'they' : 'it'} could show is marked &ldquo;cannot tell&rdquo;.
    </p>
  )
}

/** MORE THAN ONE AGENDA WAS POSTED ONLINE. TJ: "if a committee reposts its agenda for the same
 *  date ... we should make that clear when that happens". Every version is read; the last one
 *  posted is the operative notice. Times are the ONLINE copies' -- the official notice may be
 *  the paper at Town Hall, whose times are not published. */
function AgendaVersions({ vs }: { vs: AgendaVersion[] }) {
  if (!vs || vs.length < 2) return null
  return (
    <div className="mt-4 rounded-lg border p-4" style={{ borderColor: 'var(--grid)' }}>
      <p className="text-[13px] font-semibold">The town posted {vs.length} agendas online for this meeting. This review read all of them.</p>
      <p className="mt-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>Times are when each online copy was made. The official notice may be the copy posted at Town Hall, whose posting times are not published.</p>
      <ul className="mt-2 space-y-1 text-[13px]">
        {vs.map(v => (
          <li key={v.file_id}>
            <span className="font-semibold">{v.operative ? 'Last posted' : `Version ${v.version}`}</span>
            {' '}&middot; online copy made {postedAt(v.created)}
            {v.counted_hours_file_to_meeting != null && <> ({v.counted_hours_file_to_meeting} counted hours before the meeting)</>}
            {' '}&middot; <a className="underline" href={v.url} target="_blank" rel="noreferrer" style={{ color: 'var(--series-cost)' }}>as posted</a>
            {' '}&middot; <a className="underline" href={v.text_url} target="_blank" rel="noreferrer" style={{ color: 'var(--series-cost)' }}>text</a>
          </li>
        ))}
      </ul>
      {vs.filter(v => !v.operative && ((v.added_in_next?.length ?? 0) + (v.removed_in_next?.length ?? 0) > 0)).map(v => (
        <div key={'d' + v.file_id} className="mt-3 text-[13px]">
          <p className="font-semibold">What changed in the last version</p>
          {(v.added_in_next ?? []).map((x, i) => <p key={'a' + i} style={{ color: 'var(--series-revenue, #b5540f)' }}>+ {x}</p>)}
          {(v.removed_in_next ?? []).map((x, i) => <p key={'r' + i} className="line-through" style={{ color: 'var(--text-muted)' }}>&minus; {x}</p>)}
        </div>
      ))}
    </div>
  )
}

const STATUS_ORDER = ['possible — needs checking', 'cannot tell from what is published', 'clear from the record']
const STATUS_COLOR: Record<string, string> = {
  'possible — needs checking': 'var(--series-revenue, #b5540f)',
  'cannot tell from what is published': 'var(--text-muted)',
  'clear from the record': 'var(--series-cost)',
}

function hms(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60
  return (h ? h + ':' : '') + String(m).padStart(h ? 2 : 1, '0') + ':' + String(x).padStart(2, '0')
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

/** noindex from the page itself, for as long as the page is mounted. */
function useNoIndex() {
  useEffect(() => {
    const m = document.createElement('meta')
    m.name = 'robots'
    m.content = 'noindex,nofollow'
    document.head.appendChild(m)
    return () => { m.remove() }
  }, [])
}

function Quote({ children }: { children: React.ReactNode }) {
  return (
    <blockquote className="mt-1.5 pl-3 text-[14px] leading-relaxed"
      style={{ borderLeft: '3px solid var(--grid)', color: 'var(--text-primary, inherit)' }}>
      &ldquo;{children}&rdquo;
    </blockquote>
  )
}

function EvidenceItem({ e }: { e: Evidence }) {
  const link = 'underline font-semibold'
  return (
    <div className="mt-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {e.source === 'captions' ? (
          <>machine captions &middot; <a className={link} href={e.url} target="_blank" rel="noreferrer"
            style={{ color: 'var(--series-revenue, #b5540f)' }}>&#9654; {hms(e.t ?? 0)}</a></>
        ) : e.source === 'file metadata' ? 'the agenda PDF’s own metadata'
          : <>the town’s {e.source} &middot; <a className={link} href={e.url} target="_blank" rel="noreferrer"
            style={{ color: 'var(--series-cost)' }}>document</a>{e.text_url && <> &middot; <a className={link}
              href={e.text_url} target="_blank" rel="noreferrer" style={{ color: 'var(--series-cost)' }}>text</a></>}</>}
      </p>
      <Quote>{e.quote}</Quote>
      {e.note && <p className="mt-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>{e.note}</p>}
    </div>
  )
}

/** NUMBERED so a point can be referred to -- "point 4" in an email or at a meeting --
 *  and linked to directly: …/oml#point-4. TJ, 8 October 2026. The number is the point's
 *  place in the page's own order (status, then the file's order), which is fixed for a
 *  given review; a re-run review is a new review and may number differently. */
function FindingCard({ f, n }: { f: Finding; n: number }) {
  const color = STATUS_COLOR[f.status] ?? 'var(--text-muted)'
  return (
    <section id={`point-${n}`} className="mt-6 rounded-lg border p-4 sm:p-5 scroll-mt-20" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wider">
        <a href={`#point-${n}`} className="tnum text-[15px] font-bold no-underline" style={{ color: 'var(--text-primary)' }}>Point {n}</a>
        <span className="px-2 py-0.5 rounded" style={{ border: `1px solid ${color}`, color }}>{f.status}</span>
        <span style={{ color: 'var(--text-muted)' }}>{f.criterion} &middot; {f.bearing}{f.by === 'script' ? ' · computed, not read' : ''}</span>
      </div>
      <h3 className="mt-2 text-[18px] font-bold leading-snug">{f.title}</h3>
      <p className="mt-1 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{f.summary}</p>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            the rule &middot; {f.rule.section}
          </p>
          <Quote>{f.rule.quote}</Quote>
          <p className="mt-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>
            {f.rule.label} &middot; <a className="underline" href={f.rule.upstream} target="_blank" rel="noreferrer">publisher</a>
            {' '}&middot; <a className="underline" href={f.rule.our_copy} target="_blank" rel="noreferrer">our copy</a>
          </p>
        </div>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>the record</p>
          {f.evidence.map((e, i) => <EvidenceItem key={i} e={e} />)}
        </div>
      </div>
      {f.precedent && f.precedent.length > 0 && (
        <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            how the attorney general has read it, elsewhere
          </p>
          {f.precedent.map((p, i) => (
            <div key={i} className="mt-2">
              <p className="text-[13px]">
                <a className="underline font-semibold" href={p.our_copy} target="_blank" rel="noreferrer">{p.number || p.id}</a>
                {' '}&middot; {p.public_body}
                {' '}&middot; <span className="font-semibold">{p.holding ? `the AG found: ${p.holding}` : 'read the letter for the outcome'}</span>
              </p>
              <Quote>{p.quote}</Quote>
            </div>
          ))}
          <p className="mt-2 text-[12px]" style={{ color: 'var(--text-muted)' }}>
            A ruling on another body’s facts. It shows how the rule has been read; it is not a finding about this board.
          </p>
        </div>
      )}
      {f.deepened && ['confirmed', 'downgraded', 'upgraded', 'unresolved'].includes(f.deepened.outcome) && (
        <div className="mt-4 rounded-md p-3" style={{ background: 'var(--surface-2, rgba(127,127,127,0.07))' }}>
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            checked further &middot; {f.deepened.outcome}
            {f.deepened.status_before !== f.status && <> &middot; was: {f.deepened.status_before}</>}
          </p>
          <p className="mt-1 text-[13px] italic" style={{ color: 'var(--text-muted)' }}>{f.deepened.question}</p>
          <p className="mt-1 text-[15px] leading-relaxed">{f.deepened.summary}</p>
          {f.deepened.precedent.map((p, i) => (
            <div key={'p' + i} className="mt-2">
              <p className="text-[13px]">
                <a className="underline font-semibold" href={p.our_copy} target="_blank" rel="noreferrer">{p.number || p.id}</a>
                {' '}&middot; {p.public_body}
                {' '}&middot; <span className="font-semibold">{p.holding ? `the AG found: ${p.holding}` : 'read the letter for the outcome'}</span>
              </p>
              <Quote>{p.quote}</Quote>
            </div>
          ))}
          {f.deepened.evidence.map((e, i) => (
            <div key={'e' + i} className="mt-2">
              <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                {e.url ? <a className="underline" href={e.url} target="_blank" rel="noreferrer">
                  {e.t != null ? <>&#9654; {hms(e.t)} &middot; </> : null}{e.path.split('/').pop()}</a> : e.path.split('/').pop()}
              </p>
              <Quote>{e.quote}</Quote>
            </div>
          ))}
          <p className="mt-2 text-[12px]" style={{ color: 'var(--text-muted)' }}>
            Researched by a language model with search over every AG determination and the town&rsquo;s posted documents; every quotation checked verbatim. {f.deepened.note}
          </p>
        </div>
      )}
      <p className="mt-4 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="font-semibold">What would settle it:</span> {f.settle}
      </p>
    </section>
  )
}

export function OmlReview() {
  useNoIndex()
  const slug = omlSlugFromPath(window.location.pathname)
  const file = `oml/${slug}.json`
  const { d, err } = useReport<Review>(file)
  if (!slug) return null
  if (!d) {
    return <ReportShell tab={TAB} title="Open Meeting Law review" err={err ? 'No review has been written for this meeting.' : null}
      loading={!err} dataUrl={`/data/${file}`} />
  }
  // `order` maps the page's numbering back to the file, so a standout item links to its point.
  const order = d.findings.map((_, i) => i).sort((ia, ib) => {
    const a = d.findings[ia], b = d.findings[ib]
    return STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
      || (a.bearing === b.bearing ? 0 : a.bearing === 'raises a question' ? -1 : 1)
  })
  const findings = order.map(i => d.findings[i])
  return (
    // TITLE = THE MEETING. TJ, 13 November 2026: "points to check" read as confusing; the page is
    // named for the meeting it reviews, and the board sits above it.
    <ReportShell tab={TAB} title={`${longDate(d.date)}: Open Meeting Law review`} dataUrl={`/data/${file}`}
      kicker={d.board}
      standfirst={<>{d.disclaimer}</>}>
      <RecordLinks d={d} />
      <StageNote d={d} />
      <AgendaVersions vs={d.agenda_versions ?? []} />
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {STATUS_ORDER.map(s => (
          <div key={s} className="rounded-lg border p-3" style={{ borderColor: 'var(--grid)' }}>
            <p className="tnum text-3xl font-bold" style={{ color: STATUS_COLOR[s] }}>
              {d.counts[s] ?? 0} <span className="text-[14px] font-semibold">point{(d.counts[s] ?? 0) === 1 ? '' : 's'}</span>
            </p>
            <p className="text-[13px] font-semibold">{s}</p>
            <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>{d.statuses[s]}</p>
          </div>
        ))}
      </div>
      {d.standout && <StandoutBlock items={d.standout} findings={d.findings} order={order} />}
      {d.overall && <p className="mt-5 text-[16px] leading-relaxed max-w-3xl">{d.overall}</p>}

      {findings.map((f, i) => <FindingCard key={i} f={f} n={i + 1} />)}

      <H2>What no published record can show</H2>
      <ul className="mt-2 list-disc pl-5 space-y-1 text-[15px]" style={{ color: 'var(--text-secondary)' }}>
        {d.cannot_see.map((c, i) => <li key={i}>{c}</li>)}
      </ul>

      <H2>How this was read</H2>
      <Body>
        A language model ({d.written.model}) read the posted agenda, the town’s minutes, the machine captions of
        the recording and the law — G.L. c.30A as the Legislature publishes it, 940 CMR 29.00, and the
        Attorney General’s checklists and guidance. The notice arithmetic was computed by a script, not read.
        Every quotation above was checked word for word against its source by the script;
        {d.dropped.length ? ` ${d.dropped.length} point${d.dropped.length === 1 ? ' was' : 's were'} dropped because a quotation was not.` : ' none was dropped.'}
        {' '}Captions are machine speech recognition: they locate a moment, and the recording at that moment is
        what to check. Written {d.written.at.slice(0, 10)}.
      </Body>
    </ReportShell>
  )
}
