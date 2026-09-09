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

/** How a READER groups these, which is not how we built them.
 *
 *  The page used to have two sections -- "the reports" (React pages) and "the written
 *  analyses" (Markdown) -- which is a fact about our implementation and nothing a
 *  resident cares about. It also showed several subjects TWICE, because Monty Tech and
 *  special education each have both a page and a document. TJ: "monty tech being in the
 *  'written' section seems wrong. I think a breakdown of school vs town to start is
 *  good, then subcategories might help."
 *
 *  So: grouped by subject, one entry per subject, and where a page and a document cover
 *  the same ground the page wins. The grouping is declared in build_reports_index.py,
 *  which refuses to write if a report falls into no category — the failure this index
 *  exists to prevent, arriving through the feature meant to organise it. */
type Group = {
  key: string; title: string
  sections: { title: string; ids: string[] }[]
}

type Payload = {
  generated: string
  caveat: { headline: string; body: string; checkable: string; corrections: string }
  reports: Report[]
  pages: Page[]
  groups: Group[]
  superseded: Record<string, string>
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
  addsup: '\u{1F9ED}',      // the synthesis: a compass, not a subject
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

/** The method document, pulled out of the list and given the last section. */
const SHOW_YOUR_WORK = 'show-your-work'

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

  // Found by id rather than by position. If it is ever renamed the section disappears
  // rather than promoting whatever happened to be last — a silently wrong feature is
  // worse than an absent one, and the index's own --check will notice the document.
  const syw = d.reports.find(r => r.id === SHOW_YOUR_WORK)

  // Pages and documents in one lookup: the grouping addresses both by id and does not
  // care which kind a report is.
  const byId: Record<string, { title: string; about: string; url: string }> =
    Object.fromEntries([...d.reports, ...d.pages].map(r => [r.id, r]))
  const addsup = d.pages.find(r => r.id === 'addsup')
  // What the page draws: the grouped subjects, plus the two that get sections of their own.
  const shown = d.groups.reduce((n, g) =>
    n + g.sections.reduce((m, sec) => m + sec.ids.length, 0), 0)
    + (addsup ? 1 : 0) + (syw ? 1 : 0)

  return (
    <>
      <header className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
          Reports and analyses
        </h1>
        {/* THE COUNT IS WHAT THE PAGE ACTUALLY SHOWS.
            It read "32 analyses" while 25 were drawn, because seven documents are now
            superseded by a page covering the same subject and are reached from that page
            instead. A standfirst that promises more than the page holds is the small
            version of the failure this whole index exists to prevent. Derived, so it
            cannot drift again. */}
        <p className="max-w-3xl text-[15px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          {shown} analyses of the town's money, written by this project from records the
          town and district published and from documents obtained by request. Every figure
          in one is recomputed from the data on every build, and every one of them prints.
        </p>
      </header>

      {/* THE CAVEAT STAYS, BUT COLLAPSED.
          It was three paragraphs under a "Read this first" flag, immediately below a
          three-sentence standfirst -- so the page opened with roughly 150 words of
          throat-clearing before a single report. TJ: "this is too much text... if you
          want to make it expandable then cool."

          The ONE thing a reader must not miss is that these are not the town's
          documents, so that line stays visible at full weight. The three paragraphs
          explaining how to check them, and that corrections are left in the text, are
          for somebody who has decided to rely on a figure -- which happens after they
          have found one, not before.

          This is the exception rule 7a names: a genuine warning about whether to trust
          what follows leads. It does not license three paragraphs of it. */}
      <div className="mx-auto max-w-6xl px-5 mt-6">
        <details className="card p-4"
          style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <summary className="cursor-pointer list-none flex items-baseline gap-2
                              flex-wrap">
            <span className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--status-warning)' }}>Read this first</span>
            <span className="text-[15px] font-bold">{d.caveat.headline}</span>
            <span className="text-[12px] underline" style={{ color: 'var(--text-muted)' }}>
              how to check any of it
            </span>
          </summary>
          <div className="space-y-3 text-sm leading-relaxed max-w-3xl mt-3"
            style={{ color: 'var(--text-secondary)' }}>
            <p>{d.caveat.body}</p>
            <p>{d.caveat.checkable}</p>
            <p>{d.caveat.corrections}</p>
          </div>
        </details>
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
      {/* THE SYNTHESIS GOES FIRST, AND ALONE.
          It is the only report on this page that is not about a subject — it reads the
          conclusions out of all the others. Somebody arriving at the Analyses door
          without a specific question wants this one, and somebody with a question will
          scroll past it to the categories. Both are served by putting it above them
          rather than inside a group where it would sit as the fifteenth card. */}
      {/* mb-6 below is not decoration. `Section` carries `border-t`, so the first
          section's rule is drawn immediately under whatever precedes it — and with margin
          above this card and none below, the rule landed flush on its bottom edge. TJ:
          "the horizontal rule sits right on the edge of that report button." The gap an
          element needs from its container's edge is its INSET, and an asymmetric one
          reads as a mistake even when nobody can name it. */}
      {addsup && (
        <div className="mx-auto max-w-6xl px-5 mt-8 mb-6">
          <a href={addsup.url}
            className="card block p-5 transition-opacity hover:opacity-90"
            style={{ borderLeft: '4px solid var(--series-cost)' }}>
            <div className="flex items-start gap-3">
              <span aria-hidden="true" className="text-[28px] leading-none shrink-0"
                >{icon(addsup.id)}</span>
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
                  style={{ color: 'var(--text-muted)' }}>Start here</p>
                <h2 className="text-xl font-bold leading-tight mb-1.5"
                  style={{ color: 'var(--series-cost)' }}>{addsup.title} &rarr;</h2>
                <p className="text-[15px] leading-relaxed"
                  style={{ color: 'var(--text-secondary)' }}>{addsup.about}</p>
              </div>
            </div>
          </a>
        </div>
      )}

      {/* GROUPED BY SUBJECT, ONE ENTRY PER SUBJECT.
          Every report — page or document — is drawn the same way, because to a reader
          they are the same kind of thing: something this project wrote about the town's
          money. Which of them is computed on every build and which is prose with a
          verifier beside it is a fact about the report, and it belongs ON the report. */}
      {d.groups.map(g => (
        <Section key={g.key} id={g.key}
          eyebrow={g.key === 'school' ? 'Where most of the money goes'
                 : g.key === 'town' ? 'The other side of the ledger' : 'Method'}
          title={g.title}>
          {g.sections.map((sec, si) => (
            <div key={sec.title || si} className={si ? 'mt-8' : ''}>
              {sec.title && (
                <h3 className="text-[12px] font-semibold uppercase tracking-widest mb-3"
                  style={{ color: 'var(--text-muted)' }}>{sec.title}</h3>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                {sec.ids.map(id => {
                  const r = byId[id]
                  if (!r) return null
                  return (
                    <a key={id} href={r.url}
                      className="card p-4 block transition-opacity hover:opacity-90">
                      <div className="flex items-start gap-2.5">
                        <span aria-hidden="true"
                          className="text-[20px] leading-none shrink-0 mt-0.5"
                          >{icon(id)}</span>
                        <div className="min-w-0">
                          <h4 className="text-[15px] font-bold leading-tight mb-1.5"
                            style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</h4>
                          <p className="text-[13px] leading-relaxed"
                            style={{ color: 'var(--text-secondary)' }}>{r.about}</p>
                        </div>
                      </div>
                    </a>
                  )
                })}
              </div>
            </div>
          ))}
        </Section>
      ))}

      {/* SHOW YOUR WORK GETS A SECTION TO ITSELF, AND IT GOES LAST.
          TJ: "its a critical report". It is, and in the middle of a list of eighteen it
          reads as the eighteenth — a 16,000-word document about arithmetic, sitting
          between two analyses about money, where nobody would pick it out.

          It is not another analysis. It is the one that makes every other figure on this
          site checkable: each calculation with its inputs, its formula, a worked example,
          and whether the number is published by somebody, set by contract, fixed by
          statute, measured by us or assumed by us. That last distinction is rule 3, and
          this is where it is answered for every figure at once.

          LAST rather than first, deliberately. Somebody arrives wanting to know what the
          reports say; the method is what they want once they have a reason to doubt one.
          Leading with it would be the failure rule 7a describes — opening with how to
          read the thing instead of the thing. */}
      {syw && (
        <Section id="method" eyebrow="How every figure was reached"
          title="Show your work">
          <a href={syw.url}
            className="card block p-5 transition-opacity hover:opacity-90"
            style={{ borderLeft: '4px solid var(--series-cost)' }}>
            <div className="flex items-start gap-3">
              <span aria-hidden="true" className="text-[28px] leading-none shrink-0"
                >{icon(syw.id)}</span>
              <div className="min-w-0">
                <h3 className="text-xl font-bold leading-tight mb-1.5"
                  style={{ color: 'var(--series-cost)' }}>{syw.title} &rarr;</h3>
                <p className="text-[15px] leading-relaxed mb-2"
                  style={{ color: 'var(--text-secondary)' }}>{syw.about}</p>
                <p className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
                  {syw.words.toLocaleString()} words · every calculation on this site,
                  and whether each number is published, contractual, statutory, our
                  measurement or our assumption
                </p>
              </div>
            </div>
          </a>
        </Section>
      )}

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
