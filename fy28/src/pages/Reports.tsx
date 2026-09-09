import MANIFEST from '../data/agent-manifest.json'
import { useEffect, useState } from 'react'
import { Section, Note } from '../components/primitives'

/** Reports and analyses — what this project has written, as opposed to what it mirrors.
 *
 *  These lived as one group inside the source catalogue, on a shelf between the town's
 *  PDFs and the district's spreadsheets. That is the wrong shelf: everything else there
 *  was written by somebody else and republished unchanged, and these were written here.
 *  The distinction is the single most important thing a reader needs, so the caveat leads
 *  the page rather than footnoting it.
 *
 *  Every row carries the three things that make a claim checkable: the document, the
 *  script that recomputes every figure in it, and the data underneath. A reader should
 *  never have to take any of this on trust.
 */

type Report = {
  id: string; kind: string; title: string; about: string; url: string
  words: number; updated: string | null
  markdown: { url: string; bytes: number; sha256: string }
  pdf: { url: string; bytes: number } | null
  verifier: { path: string; command: string } | null
  charts: string[]
}

/** A report that is a React PAGE rather than a document. Same area, same shell, same
 *  print stylesheet; what differs is that its figures are recomputed from a published
 *  payload on every build rather than written into prose and checked afterwards. */
type Page = {
  id: string; kind: string; title: string; about: string; url: string
  component: string
  data: { url: string; bytes: number; sha256: string } | null
  generator: string | null
}

type Payload = {
  generated: string
  caveat: { headline: string; body: string; checkable: string; corrections: string }
  reports: Report[]
  pages: Page[]
  data: Record<string, { url: string; about: string }>
}

/** A glyph per report, so a wall of cards can be scanned rather than read.
 *
 *  TJ: "I want them to stand out to people somehow." These are a NAVIGATION aid and
 *  nothing more — they carry no meaning a reader has to decode, and no report depends on
 *  one to be understood. Chosen for the subject rather than the finding, because a
 *  finding can change and an icon that argued a conclusion would then be wrong in a way
 *  nothing checks.
 *
 *  An unmapped report gets the neutral document glyph rather than breaking or being
 *  dropped — a new report must always appear here, and appearing without a distinctive
 *  icon is a visible prompt to give it one. */
const ICON: Record<string, string> = {
  // the routed reports
  sped: '\u{1F9E9}',          // special education
  peers: '\u{1F5FA}\uFE0F',    // other districts
  required: '\u2696\uFE0F',    // the enforced minimum
  minaid: '\u{1F3DB}\uFE0F',   // Chapter 70, the state formula
  staffing: '\u{1F465}',      // people
  stopped: '\u{1F6D1}',       // lines taken to zero
  unwind: '\u{1F4C9}',        // grants ending
  outflow: '\u{1F68C}',       // students leaving
  montytech: '\u{1F527}',     // vocational
  leaving: '\u{1F39A}\uFE0F',  // a scenario with dials, not a measurement
  families: '\u{1F4B5}',      // what a household pays
  sportsmoney: '\u{1F3C8}',   // athletics
  insurance: '\u{1F3E5}',     // health insurance
  variance: '\u{1F4CA}',      // budget against actual
  // the written analyses
  'fy26-closeout': '\u{1F4D2}', 'fy26-closeout-town': '\u{1F3E2}',
  'budget-vs-actual': '\u{1F4CA}', 'free-cash': '\u{1F4B0}',
  athletics: '\u{1F3C6}', 'athletics-ledger': '\u{1F9FE}',
  'sped-and-the-curve': '\u{1F9E9}', 'sped-and-funds': '\u{1F9E9}',
  'fy27-and-the-override': '\u{1F5F3}\uFE0F', 'fy27-cut-reconciliation': '\u2702\uFE0F',
  'per-pupil-spending': '\u{1F393}', 'peer-districts': '\u{1F5FA}\uFE0F',
  'connecting-the-budget': '\u{1F517}', 'show-your-work': '\u{1F9EE}',
  'monty-tech': '\u{1F527}', questions: '\u2753', 'what-you-can-ask': '\u{1F50D}',
}
const icon = (id: string) => ICON[id] || '\u{1F4C4}'

/* Absolute, for the FILES this page still links — the datasets under each report and
 * the reference documents at the foot. The reports themselves are routes now, not
 * files, and a route is linked relatively like any other page on the site. */
const ABS = (u: string) => (u.startsWith('http') ? u : `${MANIFEST.site}${u}`)

export function Reports() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/reports.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(x => { if (live) setD(x) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return (
    <div className="mx-auto max-w-6xl px-5 py-20">
      <h1 className="text-2xl font-bold mb-3">The report index could not load</h1>
      <p style={{ color: 'var(--text-secondary)' }}>
        <code>/data/reports.json</code> did not answer: {err}. The analyses themselves are
        still at <code>/docs/analyses/</code>.
      </p>
    </div>
  )
  if (!d) return (
    <div className="mx-auto max-w-6xl px-5 py-20">
      <p style={{ color: 'var(--text-muted)' }}>Loading…</p>
    </div>
  )

  return (
    <>
      <header className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
          Reports and analyses
        </h1>
        <p className="max-w-3xl text-[15px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          {d.pages.length + d.reports.length} analyses written by this project, from
          records the town and district published and from documents obtained by request.
          {' '}{d.pages.length} are pages computed from a published payload on every build;
          {' '}{d.reports.length} are documents, each published as a page, a PDF and its
          source text with a checksum. Every one of them prints.
        </p>
      </header>

      {/* The caveat is the first thing on the page, at full weight, not a footnote. */}
      <div className="mx-auto max-w-6xl px-5 mt-6">
        <div className="card p-5" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--status-warning)' }}>Read this first</p>
          <p className="text-lg font-bold mb-3">{d.caveat.headline}</p>
          <div className="space-y-3 text-sm leading-relaxed max-w-3xl"
            style={{ color: 'var(--text-secondary)' }}>
            <p>{d.caveat.body}</p>
            <p>{d.caveat.checkable}</p>
            <p>{d.caveat.corrections}</p>
          </div>
        </div>
      </div>

      {/* THE PLUMBING IS NOT THE OFFER.
          Each row used to print the payload URL, the generator's filename and a full
          sha256 under a two-line description. TJ, 9 September, reading it: "why all this
          info on each report". Because I put a provenance block on an INDEX — the right
          instinct (rule 3: say which numbers are ours) applied to the wrong surface.

          A checksum is for somebody auditing a specific figure. They are not on this
          page; they are on the report, where the figure is, and every report carries its
          own provenance block naming the payload, the generator and the documents
          underneath. Printing it here costs three lines of noise per row against a
          two-line description, on the page a resident meets first.

          What a row owes a reader is: what is this, and is it checked. */}
      <Section id="pages" eyebrow="Computed on every build" title="The reports"
        lede={<p>
          Each is recomputed from published data every time the site is built, so no
          figure in one was typed by hand. Open a report to see the data and the script
          behind it.
        </p>}>
        <div className="grid gap-3 sm:grid-cols-2">
          {d.pages.map(r => (
            <a key={r.id} href={r.url}
              className="card p-4 block transition-opacity hover:opacity-90">
              <div className="flex items-start gap-2.5">
                <span aria-hidden="true" className="text-[20px] leading-none shrink-0 mt-0.5"
                  >{icon(r.id)}</span>
                <div className="min-w-0">
                  <h3 className="text-[15px] font-bold leading-tight mb-1.5"
                    style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</h3>
                  <p className="text-[13px] leading-relaxed"
                    style={{ color: 'var(--text-secondary)' }}>{r.about}</p>
                </div>
              </div>
            </a>
          ))}
        </div>
      </Section>

      <Section id="reports" eyebrow="The documents" title="The written analyses"
        lede={<p>
          Longer pieces, written rather than computed. Each opens as a page here; the
          Markdown it is rendered from and a printable copy are linked from the document
          itself, beside the sources it was built on.
        </p>}>
        <ul className="space-y-5">
          {d.reports.map(r => (
            <li key={r.id} className="card p-4">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-1.5">
                <span aria-hidden="true" className="text-[20px] leading-none"
                  >{icon(r.id)}</span>
                <h3 className="text-lg font-bold leading-tight">{r.title}</h3>
                <span className="text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
                  {r.words.toLocaleString()} words
                  {r.updated ? ` · updated ${r.updated}` : ''}
                </span>
              </div>
              <p className="text-sm leading-relaxed mb-3 max-w-3xl"
                style={{ color: 'var(--text-secondary)' }}>{r.about}</p>

              {/* THE INDEX OFFERS THE REPORT, NOT A CHOICE OF FILE FORMATS.
                  TJ, 9 September: "just dont put pdfs/markdown in the analyses
                  section". This row used to carry Read it / PDF / Source text as three
                  peer links, which made the section read as a document library — three
                  ways to obtain the same thing, and a decision to make before reading
                  any of it. Every analysis is now a page, so the page is the offer.

                  THE FILES DO NOT DISAPPEAR. Rule 12 requires our processed copy to be
                  downloadable, and it still is: the markdown and the PDF are published
                  at /docs/analyses/ and are linked from the report's own provenance
                  block, beside the sources they were built from — which is where
                  somebody who wants the file is actually standing. What changed is that
                  they are no longer presented as alternatives to reading it. */}
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] items-center">
                <a href={r.url} className="font-semibold underline"
                  style={{ color: 'var(--series-cost)' }}>Read it</a>
                {r.verifier ? (
                  <span className="text-[12px]" style={{ color: 'var(--status-good)' }}>
                    ✓ every figure recomputed by{' '}
                    <code className="text-[11px]">{r.verifier.command}</code>
                  </span>
                ) : (
                  <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
                    no verifier script — figures checked by hand
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="data" eyebrow="Underneath all of it" title="The data, linked directly"
        lede={<p>
          Nothing above has to be taken on trust. These are the same sources the analyses
          are computed from, published at stable addresses.
        </p>}>
        <div className="grid sm:grid-cols-2 gap-3">
          {Object.entries(d.data).map(([k, v]) => (
            <a key={k} href={ABS(v.url)} className="card p-4 block">
              <p className="font-semibold text-sm mb-1" style={{ color: 'var(--series-cost)' }}>
                <code>{v.url}</code>
              </p>
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                {v.about}
              </p>
            </a>
          ))}
        </div>
        <Note>
          Index generated {d.generated} by <code>scripts/build_reports_index.py</code>, so
          it cannot describe a document that is not there or omit one that is.
        </Note>
      </Section>
    </>
  )
}
