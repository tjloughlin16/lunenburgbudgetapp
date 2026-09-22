import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { isValidElement } from 'react'
import { renderMarkdown, type Heading } from '../lib/markdown'
import { FullVersion } from '../components/FullVersion'

/** First-section headings that ARE a short version. Anything else opening a document is
 *  context, and the document keeps its full length until it is edited. */
const SHORT_HEADING = /^(the short version|what this establishes|in plain terms|what we now hold|where things stand)/i
import { analysisIdFromPath } from '../routes'
import { Body, Conclusions, Grain, H2, MoreReports, ReportShell, ShortVersion, Stat, splitConclusions } from '../components/report'
import type { Conclusion } from '../components/report'

/** THE MARKDOWN ANALYSES, IN THE SAME SHELL AS EVERY OTHER REPORT.
 *
 *  WHY RENDERED AND NOT CONVERTED. Seventeen analyses are written as Markdown, verified by
 *  scripts that read the Markdown, and published at /docs/analyses/<id>.md because rule 12
 *  requires our processed copy to be downloadable. Hand-converting them into TSX would put
 *  a second copy of every figure in a file no verifier reads -- which is precisely the
 *  defect shape CLAUDE.md says almost every defect here has taken: something derived is
 *  written down, the thing it derived from moves, and nothing connects the two.
 *
 *  So the document stays the source of truth and this page RENDERS it, at request time,
 *  from the published copy. There is exactly one copy of every sentence and every figure.
 *  Change the Markdown and the page changes; there is nothing to keep in step.
 *
 *  WHAT THIS BUYS THE READER over the raw .md: the site's typography, the area navigation,
 *  a contents list, the links to the document and its verifier, and -- the reason this was
 *  asked for -- the same print stylesheet every other report has, so Save as PDF produces
 *  the same kind of document from a Markdown analysis and from a React one.
 *
 *  PRERENDERED LIKE EVERYTHING ELSE. `scripts/prerender.mjs` enumerates one route per
 *  document and renders it in headless Chrome, so a fetcher that runs no JavaScript gets
 *  the prose rather than an empty div.
 *
 *  RULE 2. Not one figure is typed into this file. Every figure on the page comes out of
 *  the document; every count in the furniture comes out of /data/reports.json.
 *
 *  RULE 7a. The document is the page. The caveat about who wrote these, the contents list
 *  and the provenance all come after it -- except the one line under the title, which is
 *  the standfirst rule 7a allows. */

type Report = {
  id: string
  title: string
  about: string
  words: number
  updated: string | null
  kind?: string
  markdown?: { url: string; bytes: number; sha256: string } | null
  pdf?: { url: string; bytes: number } | null
  verifier?: { path: string; command: string } | null
}

type Index = { generated: string; reports: Report[] }

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

/** THE MODEL-DRIVEN HALF OF A MARKDOWN REPORT.
 *
 *  WHY THIS EXISTS. This site had two kinds of report and a reader could tell: twenty-nine
 *  pages built from a generated payload and rendered through components/report.tsx -- stat
 *  rows, insight cards, the rule 7b rhythm -- and twenty markdown analyses rendered as
 *  prose, with no way to show any of it. TJ, 20 September 2026, asking why the metrics on
 *  the stabilization report did not look like the metrics everywhere else: *"this neeeds
 *  to be model driven ... is this written and built the same way the other pages are?"*
 *  It was not, and report.tsx exists precisely because a difference in PRESENTATION reads
 *  as a difference in CONFIDENCE.
 *
 *  The fix is not twenty hand-written pages. It is one renderer and twenty payloads: an
 *  analysis whose generator emits `/data/<id>.json` gets the same furniture as any other
 *  report, at the same URL, and one that does not is unchanged. So the conversion can
 *  proceed a report at a time, and nothing is a special case. */
type Payload = {
  stats?: { value: string; label: string; tone?: string }[]
  grain?: string
  conclusions?: Conclusion[]
}

export function Analysis() {
  const id = analysisIdFromPath(window.location.pathname)
  const [index, setIndex] = useState<Index | null>(null)
  const [src, setSrc] = useState<string | null>(null)
  const [model, setModel] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/reports.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setIndex(j as Index) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  // A MISSING PAYLOAD IS NOT AN ERROR. Most analyses have none yet, and a 404 here must
  // leave the page exactly as it was rather than showing a reader a failure.
  useEffect(() => {
    if (!id) return
    let live = true
    fetch(`/data/${id}.json`)
      .then(r => (r.ok ? r.json() : null))
      .then(j => { if (live && j) setModel(j as Payload) })
      .catch(() => { /* no payload for this report yet */ })
    return () => { live = false }
  }, [id])

  useEffect(() => {
    if (!id) return
    let live = true
    fetch(`/docs/analyses/${id}.md`)
      .then(r => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(t => { if (live) setSrc(t) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [id])

  // A CHART OPENS THE PAGE, ABOVE THE METRICS. TJ: *"for the pages with charts in the
  // 'short' section, put them above the metrics, just after the summary."*
  //
  // Everything the markdown carries renders BELOW the generated furniture -- that is what
  // going model-driven did -- so a chart written at the top of the document still came
  // out under the stat row and the conclusion cards. On a page whose finding IS the
  // shape, that is the wrong way round: the reader meets three numbers and six cards
  // before the one image that carries the answer.
  //
  // So any figure in the document's LEAD or in its short-version block is hoisted above
  // the metrics and rendered directly under the summary, and removed from where it was
  // so it appears once. Prose in those blocks does not move -- only figures, because a
  // paragraph above the metrics is the block of context rule 7a spent four pages getting
  // rid of.
  const isFigure = (n: React.ReactNode) => isValidElement(n) && n.type === 'figure'

  // No document named: the bare /analysis address. Unlisted, and it exists only so that
  // somebody who truncates a link lands somewhere useful rather than on the front page.
  if (!id) return <AnalysisIndex index={index} err={err} />

  const meta = index?.reports.find(r => r.id === id) ?? null
  // THE PAYLOAD GOES TO THE RENDERER, so a chart image with a component registered for
  // it is drawn rather than pictured (rule 7f). Passing `model` also means the charts and
  // the stat row read the SAME figures -- there is no second source for a picture to
  // drift from.
  const rendered = src ? renderMarkdown(src, '/docs/analyses/', model) : null

  // The document's own H1 is the report's title, and the shell has already set it. Drop
  // it from the body rather than printing the title twice.
  const body = rendered
    ? rendered.nodes.slice(rendered.headings[0]?.depth === 1 ? 1 : 0)
    : null
  const contents = (rendered?.headings ?? []).filter(h => h.depth === 2)

  // THE SHORT VERSION OF A DOCUMENT is its first section, WHEN that section is one --
  // "The short version", "What this establishes", "In plain terms". A document that
  // opens with its caveats ("What this rests on, and what it is not") or with why it
  // exists has no short version yet, and the reading-time table says so; the fix is in
  // the document, not here (rule 7a). When there is one, everything after it goes
  // behind the fold.
  const split = (() => {
    if (!body) return null
    const h2s = body.map((n, i) => (isValidElement(n) && n.type === 'h2' ? i : -1)).filter(i => i >= 0)
    if (h2s.length < 2) return null
    const first = body[h2s[0]] as React.ReactElement<{ id: string }>
    const head = contents.find(h => h.id === first.props.id)
    if (!head || !SHORT_HEADING.test(head.text)) return null
    // `rest` is split again at its own first boundary so the conclusions beyond the
    // first three can land AFTER the opening section of the fold rather than before it.
    // TJ set the order and the charts are that opening section: "all charts first. 'The
    // other findings', What is in them..." A block of findings above the charts reads as
    // a second short version, which is the thing the single fold just stopped doing.
    const nextH2 = h2s.length > 2 ? h2s[2] : body.length
    return {
      short: body.slice(h2s[0], h2s[1]),
      rest: body.slice(h2s[1]),
      restHead: body.slice(h2s[1], nextH2),
      restTail: body.slice(nextH2),
      lead: body.slice(0, h2s[0]),
    }
  })()

  // The generator owns the opening when it shipped a stat row; and the conclusions beyond
  // the first three go inside the one fold rather than beside it.
  // The figures that open the page: everything before the document's first H2, plus its
  // short-version block where it has one. `split` is null on a report with no
  // `## The short version` heading -- town-personnel and town-budgets are both like that
  // -- so this cannot be read off `split` alone, which is how the first attempt moved
  // nothing on the two pages the request was made about.
  const firstH2 = body ? body.findIndex(n => isValidElement(n) && n.type === 'h2') : -1
  const leadNodes = body ? (firstH2 < 0 ? body : body.slice(0, firstH2)) : []
  const heroFigures = [...leadNodes, ...(split?.short ?? [])].filter(isFigure)
  const isHero = (n: React.ReactNode) => heroFigures.includes(n)

  const ownsShort = !!model?.stats?.length
  const moreRows = model?.conclusions ? splitConclusions(model.conclusions, undefined)[1] : []

  const title = meta?.title
    ?? (rendered?.headings[0]?.depth === 1 ? rendered.headings[0].text : id)

  return (
    <ReportShell
      kicker="An analysis, written by this project"
      title={title}
      standfirst={meta?.about}
      err={src ? null : err}
      loading={!src && !err}
      sourceUrl={`/docs/analyses/${id}.md`}
    >
      {/* The contents list draws only where there is no fold; the fold carries its own. */}
      {contents.length > 2 && !split && (
        <nav aria-label="Contents" className="no-print card p-4 mt-8 max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>What is in it</p>
          <ul className="space-y-1">
            {contents.map((h: Heading) => (
              <li key={h.id}>
                <a href={`#${h.id}`} className="text-[13.5px] leading-snug underline"
                  style={{ color: 'var(--series-cost)' }}>{h.text}</a>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {/* THE CONCLUSIONS, IN THE SAME FURNITURE EVERY OTHER REPORT USES. Rendered above
          the document because rule 7b opens a drill-in with what it MEANS; the prose
          short version still follows, because the markdown is also what /docs serves and
          what the PDF is made from, and the two must not drift apart. */}
      {/* ONE FOLD, AND THE GENERATOR OWNS THE SHORT VERSION WHEN IT HAS ONE.
          Two bugs lived here, both introduced with the model block and both found by TJ
          reading the page rather than by any check:

          TWO EXPANDABLE SECTIONS. The extra conclusions got a `FullVersion` of their own,
          beside the one the document already had, so the page offered a reader two folds
          and no way to tell which held what. There is one fold on a report.

          AND THE SHORT VERSION TWICE. When a payload carries `stats` the generator has
          authored this page's short version -- that IS the stat row and the cards -- and
          rendering the markdown's own `## The short version` underneath says the same
          figures again in prose. Worse, pushing it into the fold puts a section headed
          "The short version" inside the full version, which is the joke TJ made when he
          saw it.

          So: `stats` present means the generator owns the opening and the markdown's
          short-version section is dropped FROM THE PAGE. It stays in the .md, which is
          what /docs serves and what the PDF is made from -- this is a rendering decision,
          not a deletion. A payload with conclusions but no stats (athletics,
          budget-vs-actual, monty-tech, whose conclusions are authored for their own React
          pages) keeps its prose short version, because nothing has replaced it. */}
      {/* The opening chart, hoisted out of the document so it sits under the summary and
          above the metrics. See `isFigure` above for why. */}
      {/* The signature image is not read, so it is not held to the reading measure:
          `max-w-3xl` is right for prose and wrong for a picture. */}
      {heroFigures.length ? (
        <div className="report-body mt-6 [&>figure]:max-w-none">{heroFigures}</div>
      ) : null}

      {model && (model.stats?.length || model.conclusions?.length) ? (
        <section data-section="conclusions" data-short="">
          {model.stats?.length ? (
            <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
              {model.stats.map(s => (
                <Stat key={s.value + s.label} value={s.value} tone={s.tone}>{s.label}</Stat>
              ))}
            </div>
          ) : null}
          {model.grain ? <Grain>{model.grain}</Grain> : null}
          {model.conclusions?.length
            ? <Conclusions rows={splitConclusions(model.conclusions, undefined)[0]} />
            : null}
        </section>
      ) : null}

      {split ? (
        <>
          <div className="report-body mt-6">{split.lead.filter(n => !isHero(n))}</div>
          {ownsShort ? null : (
            <ShortVersion>
              <div className="report-body">{split.short.filter(n => !isHero(n))}</div>
            </ShortVersion>
          )}
          {/* THE CHARTS STAY ABOVE THE FOLD. `restHead` is the document's first section
              after its short version, and on every analysis converted so far that is the
              charts. It used to open the FULL VERSION, which put every chart behind
              "Read the full analysis" — TJ, looking at the stabilization page: *"where
              did the line chart go on the repor?! I cant find it"*. It was at character
              30,280 of the rendered page against a fold at 28,783.

              That was a side effect of going model-driven rather than anyone's decision:
              the stat row and the conclusion cards took the top, and everything the
              markdown carried moved down a level with them. A chart is not supporting
              material on these pages — it is the finding in the form most readers will
              take it in, and rule 7b puts the organised categorical data in the second
              movement, not behind a disclosure.

              So the order above the fold is: metrics, grain, conclusions, charts. The
              fold then opens with "The other findings", which is what it was always for. */}
          <div className="report-body mt-6">{split.restHead}</div>
          <FullVersion what="the rest of the analysis">
            {moreRows.length > 0 ? (
              <>
                <H2 id="more-findings">The other findings</H2>
                <Conclusions rows={moreRows} noAsk short={false} />
              </>
            ) : null}
            <div className="report-body mt-6">{split.restTail}</div>
          </FullVersion>
        </>
      ) : (
        <div className="report-body mt-6">{body?.filter(n => !isHero(n))}</div>
      )}

      {/* AFTER the document, not above it. Rule 7a: the page leads with the thing, and
          the note about how to read it comes after -- except where the caveat changes
          whether a reader should trust what follows, which is /reports' own lead and is
          repeated here in one line rather than as a preface. */}
      <H2>Where this came from</H2>
      <Body>
        Nothing on this page is an official document. It was written here, from documents
        the town and district published and from records obtained by request, and it has
        not been reviewed or endorsed by the Town of Lunenburg, the School Committee, the
        Finance Committee or Lunenburg Public Schools.{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/reports')}>The report index</a> says the same thing at more length,
        and lists every analysis alongside the data underneath it.
      </Body>
      <Body>
        This page renders{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs(`/docs/analyses/${id}.md`)}>the document itself</a>, which is the
        source of truth: there is one copy of every sentence and every figure here, not a
        transcription of one.
        {meta?.verifier ? <> Every figure in it is recomputed from the underlying data
          by <code>{meta.verifier.command}</code>, which fails rather than warns.</> : null}
      </Body>

      <DocumentBar id={id} meta={meta} />

      <MoreReports />
    </ReportShell>
  )
}

/** The document's own address, filename, size and hash. Rule 12 rendered for a document
 *  this project wrote: the copy you are reading, and the copy you can keep.
 *
 *  AT THE BOTTOM, WITH THE REST OF THE PROVENANCE. It used to render in the shell's
 *  `meta` slot -- the first line under the standfirst, above the conclusions -- and TJ,
 *  reading the stabilization page: *"Markdown 1,769 words 10 KB last changed sha256
 *  7d2e63c668637e9c. why do we have that still"*.
 *
 *  The answer is that it is load-bearing and it was misplaced, which is why this is a
 *  MOVE and not a deletion. Rule 12 requires the downloadable copy and its sha256,
 *  because a file can be replaced in place without its address changing; `/docs` serves
 *  that .md, the PDF is rendered from it, and llms.txt sends agents that cannot run
 *  JavaScript straight to it. Deleting the bar would take the only link to any of that
 *  off the page.
 *
 *  But rule 7a says a page opens with the thing, and file metadata is not the thing --
 *  and no report built from a React page has ever put it up there, so it was also the
 *  last visible seam between the two kinds of report that rule 7d exists to erase. It
 *  belongs where every other report keeps its provenance: after the document, next to
 *  the sentence explaining what the document is. */
function DocumentBar({ id, meta }: { id: string; meta: Report | null }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-4 text-[12.5px]"
      style={{ color: 'var(--text-muted)' }}>
      <a className="underline no-print" style={{ color: 'var(--series-cost)' }}
        href={abs(`/docs/analyses/${id}.md`)}>Markdown</a>
      {meta?.pdf && (
        <a className="underline no-print" style={{ color: 'var(--series-cost)' }}
          href={abs(meta.pdf.url)}>PDF</a>
      )}
      {meta?.words ? <span>{meta.words.toLocaleString()} words</span> : null}
      {meta?.markdown ? <span>{kb(meta.markdown.bytes)}</span> : null}
      {meta?.updated ? <span>last changed {meta.updated}</span> : null}
      {meta?.markdown ? (
        <span className="break-all">sha256 {meta.markdown.sha256.slice(0, 16)}&hellip;</span>
      ) : null}
    </div>
  )
}

/** The bare `/analysis` address. Not linked from anywhere and not in the sitemap -- see
 *  UNLISTED in routes.ts. `/reports` is the index a reader is sent to. */
function AnalysisIndex({ index, err }: { index: Index | null; err: string | null }) {
  return (
    <ReportShell
      kicker="Written by this project"
      title="The analyses"
      standfirst="Every document this project has written, rendered on the site. The full index, with the data underneath each one, is at /reports."
      err={err}
      loading={!index && !err}
      dataUrl="/data/reports.json"
    >
      <div className="grid gap-2 mt-8 sm:grid-cols-2">
        {(index?.reports ?? []).filter(r => r.kind !== 'page').map(r => (
          <a key={r.id} href={abs(`/analysis/${r.id}`)}
            className="card block p-4 min-h-[44px] transition-opacity hover:opacity-90">
            <span className="text-[15px] font-bold leading-tight"
              style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</span>
            <span className="block text-[13px] leading-relaxed mt-1.5"
              style={{ color: 'var(--text-secondary)' }}>{r.about}</span>
          </a>
        ))}
      </div>
    </ReportShell>
  )
}
