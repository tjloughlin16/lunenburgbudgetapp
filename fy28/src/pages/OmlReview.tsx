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
type Finding = {
  criterion: string; title: string; status: string; bearing: string; summary: string
  rule: Rule; evidence: Evidence[]; settle: string; by: 'model' | 'script'
}
type Review = {
  title: string; disclaimer: string; board: string; board_slug: string; date: string
  video_url: string; agenda_url: string; minutes_url: string; our_minutes_page: string
  overall: string; counts: Record<string, number>; findings: Finding[]
  dropped: { title: string; why: string }[]; cannot_see: string[]; statuses: Record<string, string>
  written: { model: string; at: string; cost_usd: number }
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
    return <ReportShell tab={TAB} title="Open Meeting Law: points to check" err={err ? 'No review has been written for this meeting.' : null}
      loading={!err} dataUrl={`/data/${file}`} />
  }
  const findings = [...d.findings].sort((a, b) =>
    STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
    || (a.bearing === b.bearing ? 0 : a.bearing === 'raises a question' ? -1 : 1))
  return (
    <ReportShell tab={TAB} title="Open Meeting Law: points to check" dataUrl={`/data/${file}`}
      kicker={`${d.board} · ${longDate(d.date)}`}
      standfirst={<>{d.disclaimer}</>}>
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
      {d.overall && <p className="mt-5 text-[16px] leading-relaxed max-w-3xl">{d.overall}</p>}
      <p className="mt-2 text-[13px]" style={{ color: 'var(--text-muted)' }}>
        <a className="underline" href={d.agenda_url} target="_blank" rel="noreferrer">The agenda</a> &middot;{' '}
        {d.minutes_url
          ? <a className="underline" href={d.minutes_url} target="_blank" rel="noreferrer">the town’s minutes</a>
          : <span>the town’s minutes (not yet posted)</span>} &middot;{' '}
        <a className="underline" href={d.video_url} target="_blank" rel="noreferrer">the recording</a> &middot;{' '}
        <a className="underline" href={d.our_minutes_page}>our minutes of the recording</a>
      </p>

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
