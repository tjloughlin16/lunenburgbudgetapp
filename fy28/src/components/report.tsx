import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { AREA_LABEL, AREA_TABS, LABEL, SLUG, areaOf, type Tab } from '../routes'

/** THE ONE SHELL EVERY REPORT ON THIS SITE IS BUILT IN.
 *
 *  WHY IT EXISTS. Twenty-odd analysis pages were written one at a time, each inventing its
 *  own header, its own loading sentence, its own error card and its own provenance block.
 *  They said the same things in slightly different words and set them at slightly different
 *  sizes, and a reader takes a difference in PRESENTATION for a difference in CONFIDENCE.
 *  Four readings of one archive must look like four readings of one archive.
 *
 *  WHAT IS SHARED IS THE FRAME, NEVER A FIGURE. Rule 2 governs this file absolutely: no
 *  component here accepts, computes, holds or prints a number of its own. Every figure on
 *  every report arrives from that report's own generated payload. This file is furniture.
 *
 *  THE RHYTHM IS RULE 7b, AND IT IS A COMPONENT RATHER THAN A CONVENTION. A drill-in page
 *  opens with what it MEANS -- conclusions a reader could repeat at a meeting -- then the
 *  organised categorical data that supports them, then the raw table, the method and what
 *  it does not show. `Section` takes that as a named prop, so the order is legible in the
 *  page source and a page that skips a movement is visible in a diff.
 *
 *  THE HYPOTHESIS BOX HAS ITS OWN COLOUR AND ITS OWN LABEL. Rule 7: a figure is a fact and
 *  an explanation for it is not, and the whole of this project's error history is the two
 *  being set in the same voice one paragraph apart.
 *
 *  PRINTING IS A FIRST-CLASS OUTPUT, NOT AN ACCIDENT. Residents and officials take these
 *  to meetings on paper. The shell puts a Print / Save as PDF control on every report and
 *  marks the structure the print stylesheet in index.css needs -- see `.report`,
 *  `.no-print`, `.print-only` and `.avoid-break` there. Nothing renders the PDF for us: the
 *  browser does, from the same DOM a reader sees, which is the only way the paper copy
 *  cannot drift from the page. */

/* ---- the payload shapes the generated reports share ---------------------- */

export type Said = {
  key: string; board: string; date: string; quote: string; why: string
  cite: string; town: string
  // Optional because the generators differ: some name the KIND of meeting document a
  // quote came from and some do not, and a page must print what its own payload holds
  // rather than a blank where a field would be.
  kind?: string
  who?: string
}

export type Source = {
  path: string; sha256: string; bytes: number; url: string; docs_url: string
  table: string; publisher: string; note: string
}

export type Minutes = {
  published: number; held: number; searchable: number; unsearchable: number
  image_scan: number; searchable_share: number; text_files_present: number
  first_date: string; last_date: string
}

export type Base = {
  about: string; grain: string; sources: Source[]
  said: Said[]; searched: { term: string; documents: number }[]
  minutes: Minutes; not_established: string[]; closes: string
  conclusions?: Conclusion[]
}

/** WHAT A REPORT ESTABLISHES, computed by the generator that computed its figures.
 *
 *  Written in Python, in `scripts/conclusions.py`, and shipped in the payload. The page
 *  RENDERS these; it does not restate them. That is rule 2 extended from figures to the
 *  claims figures support -- a sentence in a `.tsx` carrying an amount is prose that
 *  ships and nothing recomputes it, which is this project's oldest defect shape.
 *
 *  `figures` is every amount the text states, keyed by name, each with the value it was
 *  derived from and the exact string it renders as. A verifier recomputes the value; the
 *  Python checker asserts the string is in the prose and that no unregistered digit is.
 *
 *  `kind` is the rule 7 line and it is drawn in the page, not only in the data: a
 *  measurement and an explanation for a measurement are never set in the same voice. */
export type Conclusion = {
  id: string
  /** ONE line: what the metric IS. */
  claim: string
  /** ONE line: what follows from it. */
  so_what: string
  /** The expansion. Everything a reader who wants the working would want, and nothing
   *  they need in order to understand the two visible lines -- if the expansion is
   *  load-bearing for comprehension, the card has failed. */
  detail: string
  /** The key in `figures` to set large above the claim, where the finding IS an amount. */
  figure?: string
  figures: Record<string, { value: number | string; text: string; unit: string }>
  kind: 'measured' | 'hypothesis'
  basis: string
  not_shown: string
  see: { slug: string; label: string }[]
}

/* ---- headings and prose -------------------------------------------------- */

export function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

export function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[15px] font-bold mt-9 mb-1 max-w-2xl">{children}</h3>
}

export function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

export function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div className="avoid-break">
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/* ---- rule 7b, as a component --------------------------------------------- */

/** The three movements of a drill-in, in the order rule 7b fixes them.
 *
 *  `conclusions` is what the page establishes, in sentences. `categorical` is the
 *  breakdown that supports them -- by year, by category, by school -- and is where charts
 *  belong. `raw` is the table, the method, the provenance and what the page does not show.
 *
 *  A page may have several `categorical` sections. It should have exactly one of the other
 *  two, and they are the first and last things on it. */
export function Section({ kind, id, title, children }: {
  kind: 'conclusions' | 'categorical' | 'raw'
  id?: string; title?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <section id={id} data-section={kind}
      className="report-section scroll-mt-[calc(var(--header-h)+1rem)]">
      {title ? <H2>{title}</H2> : null}
      {children}
    </section>
  )
}

/** One conclusion, in the voice rule 7b's first movement requires: a claim a reader
 *  could repeat at a meeting.
 *
 *  TWO MODES, AND THE DIFFERENCE IS WHETHER THE FINDING HAS A HEADLINE FIGURE.
 *
 *    - WITHOUT `figure`, the card is labelled `Finding 1` and leads with the claim. This
 *      is the right shape where the finding is a relation rather than an amount -- "two
 *      sources report different counts and cannot be reconciled" has no number to set.
 *    - WITH `figure`, the amount is set large above the claim, numbered `01`. This is the
 *      right shape where the finding IS an amount, and it is what /what-sports-cost has
 *      always done. The figure is passed in already formatted by the page; rule 2 means
 *      nothing here computes or rounds it.
 *
 *  `tone` colours the figure, or draws a rule across the top of a card that has none,
 *  where the page's findings map onto its own chart hues.
 *
 *  Both modes are here rather than in two components because they are one thing said two
 *  ways, and a reader must not read the difference as a difference in confidence. */
export function Insight({ n, tone, figure, headline, children }: {
  n?: number; tone?: string; figure?: string
  headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5 avoid-break"
      style={tone && !figure ? { borderTop: `3px solid ${tone}` } : undefined}>
      {figure !== undefined ? (
        <div className="flex items-baseline gap-3">
          {n === undefined ? null : (
            <span className="text-[11px] font-bold tabular-nums"
              style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
          )}
          <span className="text-2xl font-bold tracking-tight tnum"
            style={tone ? { color: tone } : undefined}>{figure}</span>
        </div>
      ) : n === undefined ? null : (
        <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      )}
      <p className={figure !== undefined
        ? 'text-[15.5px] font-semibold leading-snug mt-2'
        : 'text-[17px] font-bold leading-snug'}>{headline}</p>
      <div className={figure !== undefined
        ? 'text-[13.5px] leading-relaxed mt-2'
        : 'text-[14px] leading-relaxed mt-2.5'}
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** A report's conclusions, rendered from its payload.
 *
 *  RULE 7b's FIRST MOVEMENT, and the top of every drill-in. What the page MEANS, before
 *  what it holds -- three or four claims a reader could repeat at a meeting, then the
 *  categorical breakdown, then the raw table.
 *
 *  NOTHING HERE IS TYPED. Every word and every figure comes out of the payload, so a page
 *  cannot state a conclusion its own data no longer supports, and /what-it-all-adds-up-to
 *  can carry the same sentences without either copy drifting from the other.
 *
 *  WHAT IS ON THE CARD AND WHY EACH PART IS THERE. The claim, large, because it is the
 *  thing. The detail under it. Then the two halves rule 7 insists on: what the claim rests
 *  on, and what it does not show -- set smaller and quieter than the claim, but on the
 *  same card, because a caveat on another card is a caveat nobody reads.
 *
 *  A HYPOTHESIS IS DRAWN DIFFERENTLY. `kind: 'hypothesis'` gets the warning rule and its
 *  own label, the same treatment `Maybe` gives. A figure is a fact and an explanation for
 *  it is not, and the whole of this project's error history is those two set in one voice
 *  a paragraph apart. */
export function Conclusions({ rows, collapse, reportUrl }: {
  rows?: (Conclusion & { report_url?: string })[]
  /** Collapse the evidence behind a `<details>`, leaving the claim and its figure. Used
   *  by /what-it-all-adds-up-to, which carries a conclusion from EVERY report and so
   *  accumulates weight faster than any single one of them.
   *
   *  TJ, reading that page: *"the boxes are very text heavy. I think we need the
   *  conclusion clear, but the section is collapsed by default, and expandable, with a
   *  link to drill in for more details."* Sixteen claims each with a paragraph of basis
   *  under it is a wall, and the wall hides the thing the page exists to show -- that the
   *  conclusions are individually short and collectively add up to something.
   *
   *  `<details>` rather than state: no JavaScript, it works before hydration, and it
   *  PRINTS OPEN, which matters because these get taken to meetings on paper. Same
   *  mechanism as the caveat block on /reports.
   *
   *  WHAT MUST NOT HAPPEN, and it is the trap in this whole idea: a claim visible with its
   *  limits behind a click is a page quietly more confident than the reports it
   *  summarises. So the summary line carries the first line of `not_shown` itself, clipped
   *  by CSS rather than by cutting the string -- the EXISTENCE of a limit is visible
   *  without expanding anything, and nothing is rewritten to make it fit. */
  collapse?: boolean
  /** Where "read the full report" goes, for a block of one report's conclusions. A row
   *  carrying its own `report_url` -- as the master report's headlines do -- wins. */
  reportUrl?: string
}) {
  if (!rows || !rows.length) return null
  return (
    <>
    <div className="grid gap-4 mt-5 md:grid-cols-2">
      {rows.map((c, i) => {
        const fig = c.figure ? c.figures[c.figure]?.text : undefined
        const unit = c.figure ? c.figures[c.figure]?.unit : undefined
        const guess = c.kind === 'hypothesis'
        const href = c.report_url ?? reportUrl
        return (
          <div key={c.id} id={c.id}
            className="card p-5 avoid-break scroll-mt-[calc(var(--header-h)+1rem)]"
            style={guess ? { borderTop: '3px solid var(--status-warning)' } : undefined}>
            <div className="flex items-baseline gap-3">
              <span className="text-[11px] font-bold tabular-nums"
                style={{ color: 'var(--text-muted)' }}>{String(i + 1).padStart(2, '0')}</span>
              {fig ? (
                <span className="text-2xl font-bold tracking-tight tnum">{fig}</span>
              ) : null}
              {/* THE UNIT, ON THE NUMBER. Rule 7 in visual form: dollars are not students
                  and a placement is not a cost, and this page sets figures from sixteen
                  reports at six different grains side by side. A bare `10` in a stat box
                  abandons that at the moment a reader is most likely to quote it. */}
              {unit ? (
                <span className="text-[13px] font-semibold"
                  style={{ color: 'var(--text-secondary)' }}>{unit}</span>
              ) : null}
              </div>
            {guess ? (
              /* THE EPISTEMIC LABEL SURVIVES THE TRIM. Shortening these cards removed the
                 sentences that used to carry "this is a scenario, not something that
                 happened" in prose -- so the label has to do it, and it has to be legible
                 next to fourteen measured cards rather than tucked beside the figure. A
                 reader who takes a scenario's number for a measurement has been actively
                 misled, which is worse than any sentence that was cut. */
              <p className="text-[11px] font-semibold uppercase tracking-widest mt-1.5"
                style={{ color: 'var(--status-warning)' }}>
                A scenario or an explanation &mdash; nothing here tests it
              </p>
            ) : null}
            {/* THE CARD IS FOUR THINGS AND NOT ONE MORE: the metric with its unit above,
                one line saying what the metric is, one line saying what follows, and the
                expansion. TJ: "we cannot have BOLD context lines that are 3-5 lines...
                which means we have to be HYPER clear about what the metric represents,
                and what conclusion to draw from it without needing a full paragraph of
                context for each." The two lines are length-capped in conclusions.py, so a
                card that grows a third idea fails the build rather than the eye. */}
            <p className="text-[15.5px] font-semibold leading-snug mt-2">{c.claim}</p>
            <p className="text-[14px] leading-snug mt-1.5"
              style={{ color: 'var(--text-secondary)' }}>{c.so_what}</p>
            {collapse && href ? (
              <p className="text-[13px] mt-2.5 no-print">
                <a className="underline font-semibold"
                  style={{ color: 'var(--series-cost)' }}
                  href={abs(href)}>Read the full report &rarr;</a>
              </p>
            ) : null}
            {collapse ? (
              <details className="mt-3">
                {/* A CONTROL, NOT A SENTENCE. TJ: "'The evidence, and what it does not
                    show' is not needed. Just make it obvious that each box can be
                    expanded... we dont need all these words in each box. its
                    overwhelming." A summary that explains what is inside costs a line and
                    says what one click would show.
                    AND IT MUST NOT READ AS A LINK. There is a real link on this card, to
                    the full report, and it carries an arrow. This carries a chevron that
                    turns, which is the affordance people already read as "opens here". */}
                <summary className="cursor-pointer list-none inline-flex items-center gap-1.5
                                    text-[12.5px] font-semibold"
                  style={{ color: 'var(--text-muted)' }}>
                  <span className="conc-chev inline-block transition-transform"
                    aria-hidden="true">&#9656;</span>Details
                </summary>
                <ConclusionEvidence c={c} />
              </details>
            ) : (
              <ConclusionEvidence c={c} />
            )}
          </div>
        )
      })}
    </div>
    <AskPrompt />
    </>
  )
}

/** The detail, the links out, the basis and the limits. Rendered inline on a report and
 *  behind a `<details>` on the synthesis page -- the SAME nodes either way, so a reader
 *  who expands one gets what a reader of the report already had. */
function ConclusionEvidence({ c }: { c: Conclusion }) {
  return (
    <>
      <p className="text-[14px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{c.detail}</p>
      {c.see.length ? (
        <p className="text-[13px] mt-3 no-print">
          {c.see.map((l, j) => (
            <span key={l.slug}>
              {j ? ' \u00b7 ' : ''}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(l.slug)}>{l.label} &rarr;</a>
            </span>
          ))}
        </p>
      ) : null}
      <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold uppercase tracking-widest text-[10.5px]">
            What it rests on
          </span>{' '}
          {c.basis}
        </p>
        <p className="text-[12.5px] leading-relaxed mt-2"
          style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold uppercase tracking-widest text-[10.5px]">
            What it does not show
          </span>{' '}
          {c.not_shown}
        </p>
      </div>
    </>
  )
}

/** THE OFFER, PUT WHERE THE QUESTION HAPPENS.
 *
 *  TJ: *"i think we should put that line to suggest the 'ask' after every conclusion
 *  section."* Directly after the conclusions and before the categorical data -- not at the
 *  foot of the page. Somebody who has just read that two fifths of what the town spends on
 *  out-of-district placement never touches the budget they vote on has a question RIGHT
 *  THEN, and four sections later they have either found it themselves or stopped reading.
 *
 *  IT IS IN THE SHELL SO A REPORT CANNOT FORGET IT, and it renders only where there are
 *  conclusions to have raised a question in the first place: an orphan prompt under an
 *  empty section is an invitation to ask about nothing.
 *
 *  THE WORDING IS THE WHOLE OF THE CARE HERE. It must not read as *we did not bother, go
 *  and ask* -- these reports exist to answer things, and an offer that implies otherwise
 *  is worse than no offer. So it says what the report DID reach first, and offers the
 *  remainder. No exclamation, no verb in the imperative shouting at anybody, and no count
 *  of questions received: zero is the honest number today and it is also the least
 *  inviting thing this could print.
 *
 *  AND IT SAYS WHAT IS NOT REQUIRED, rather than claiming anonymity. TJ asked for the
 *  anonymity to be said; the precise version of it is "no name or email needed", which is
 *  true whichever way the reader goes. A flat "anonymous" would not be: the form has an
 *  optional email field, and somebody who fills it in is no longer anonymous to us. A
 *  promise conditional on a choice the reader has not yet made is not a promise this
 *  project makes. What is actually kept -- a truncated salted hash of the IP for rate
 *  limiting, never the address; the email only if given; a coarse country -- is set out on
 *  /ask-a-question under "What we keep", one click away, so this line does not restate it. */
function AskPrompt() {
  return (
    <p className="text-[13.5px] leading-relaxed max-w-2xl mt-5 no-print"
      style={{ color: 'var(--text-muted)' }}>
      Those are the answers this report could reach from the documents behind it. If the
      one you came for is not among them,{' '}
      <a className="underline" style={{ color: 'var(--series-cost)' }}
        href={abs('/ask-a-question')}>ask us &mdash; no name or email needed</a>.
    </p>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
export function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl avoid-break"
      style={{ borderLeft: '4px solid var(--axis)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>What this does not show</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </div>
    </div>
  )
}

/** A hypothesis, marked as one. Never rendered in the same voice as a measurement. */
export function Maybe({ settle, children }: {
  settle: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-4 mt-4 max-w-2xl avoid-break"
      style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>
        A possible explanation &mdash; nothing here tests it
      </p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
        <p className="mt-2.5"><strong>What would settle it:</strong> {settle}</p>
      </div>
    </div>
  )
}

/** What GRAIN this report is at, said at the top of it. Reports exist separately because
 *  their grains differ, so each one states its own before anything else. */
export function Grain({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-3.5 mt-6 max-w-2xl avoid-break"
      style={{ borderLeft: '4px solid var(--fund-school)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>What this report counts</p>
      <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </p>
    </div>
  )
}

export function Quote({ q }: { q: Said }) {
  return (
    <div className="card p-4 avoid-break">
      <p className="text-[15px] leading-relaxed">&ldquo;{q.quote}&rdquo;</p>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {q.board} &middot;{q.kind ? ` ${q.kind.toLowerCase()} \u00b7` : ''} {q.date} &middot;{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs(q.cite)}>our copy</a>{' '}
        &middot; <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={q.town}>the town&rsquo;s</a>
      </p>
      <p className="text-[13.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{q.why}</p>
    </div>
  )
}

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

/** Rule 12, rendered: the address, the publisher's own filename, our copy, the sha256.
 *
 *  Marked `report-provenance` so the print stylesheet can guarantee it survives onto
 *  paper. A printed figure whose source did not print is a figure nobody can check. */
export function Provenance({ sources }: { sources: Source[] }) {
  return (
    <div className="report-provenance grid gap-3 mt-5 sm:grid-cols-2">
      {sources.map(s => (
        <div key={s.path} className="card p-4 avoid-break">
          <p className="text-[13.5px] font-bold leading-snug break-words">
            {s.path.split('/').pop()}
          </p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {s.publisher}
          </p>
          <p className="text-[13px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>{s.note}</p>
          <p className="text-[11.5px] mt-2.5" style={{ color: 'var(--text-muted)' }}>
            table <code>{s.table}</code> &middot; {kb(s.bytes)}
          </p>
          <p className="text-[11px] mt-1 break-all" style={{ color: 'var(--text-muted)' }}>
            sha256 {s.sha256.slice(0, 16)}&hellip;
          </p>
          <p className="text-[12px] mt-2">
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs(s.docs_url)}>our copy</a>
            {s.url ? <> &middot; <a className="underline"
              style={{ color: 'var(--series-cost)' }} href={s.url}>the publisher&rsquo;s</a></> : null}
          </p>
        </div>
      ))}
    </div>
  )
}

/** The denominator, printed beside every search. A grep that finds nothing prints
 *  nothing, and nothing reads as "nobody said it". */
export function Coverage({ m, searched }: {
  m: Minutes; searched: { term: string; documents: number }[]
}) {
  return (
    <>
      <div className="flex flex-wrap gap-x-10 gap-y-4 mt-5">
        {searched.map(s => (
          <div key={s.term}>
            <div className="text-2xl font-bold tnum">{s.documents}</div>
            <div className="text-[12.5px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              documents mention &ldquo;{s.term}&rdquo;
            </div>
          </div>
        ))}
      </div>
      <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-muted)' }}>
        Searched {m.searchable.toLocaleString()} of the {m.held.toLocaleString()} meeting
        documents this archive holds ({Math.round(m.searchable_share * 100)}%), covering{' '}
        {m.first_date} to {m.last_date}. The other{' '}
        {m.unsearchable.toLocaleString()} carry no text a search can match &mdash;{' '}
        {m.image_scan.toLocaleString()} of them are image scans awaiting OCR. An empty
        result above is a statement about what can be read, never about what was said.
      </p>
    </>
  )
}

export function NotEstablished({ rows, closes }: { rows: string[]; closes: string }) {
  return (
    <>
      <ul className="mt-5 space-y-3 max-w-2xl">
        {rows.map(r => (
          <li key={r} className="text-[14px] leading-relaxed pl-4 border-l-2"
            style={{ color: 'var(--text-secondary)', borderColor: 'var(--axis)' }}>{r}</li>
        ))}
      </ul>
      <div className="card p-4 mt-5 max-w-2xl avoid-break"
        style={{ borderLeft: '4px solid var(--status-good)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>What would close these</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {closes} Every limit on this page is also a row in{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/what-we-cannot-answer')}>what we cannot answer</a>, which is the
          single registry the records request reads from.
        </p>
      </div>
    </>
  )
}

/* ---- moving between reports ---------------------------------------------- */

/** The four special education reports, as links, at the foot of each of them. Named for
 *  what each COUNTS, so a reader crossing from one to another is told the grain changed. */
export function OtherReports({ here }: { here: string }) {
  const all = [
    { slug: 'how-many-students-are-on-an-iep', name: 'How many students', what: 'children' },
    { slug: 'where-students-go-instead', name: 'Who leaves, and where they go', what: 'children, with no disability flag' },
    { slug: 'what-special-education-costs', name: 'What it costs, and what comes back', what: 'dollars' },
    { slug: 'who-ends-up-out-of-district', name: 'The route out of district', what: 'placements' },
  ].filter(r => r.slug !== here)
  return (
    <div className="grid gap-3 mt-5 sm:grid-cols-3">
      {all.map(r => (
        <a key={r.slug} href={abs(`/${r.slug}`)}
          className="card block p-4 min-h-[44px] transition-opacity hover:opacity-90 avoid-break">
          <span className="text-[15px] font-bold leading-tight"
            style={{ color: 'var(--series-cost)' }}>{r.name} &rarr;</span>
          <span className="block text-[12.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            counts {r.what}
          </span>
        </a>
      ))}
    </div>
  )
}

/** Every other report in the Analyses area, at the foot of each of them.
 *
 *  Read off `AREA_TABS.analyses` rather than listed here, for the reason rule-of-thumb 1
 *  in CLAUDE.md gives: a hand-kept list of one's own pages is the artefact that goes stale
 *  first and is least likely to be noticed doing it. A report added to the area appears
 *  here the same day. */
export function MoreReports({ here }: { here?: Tab }) {
  const others = AREA_TABS.analyses.filter(t => t !== here && t !== 'reports')
  return (
    <div className="no-print">
      <H2>Every other report</H2>
      <div className="grid gap-2 mt-5 sm:grid-cols-2 lg:grid-cols-3">
        {others.map(t => (
          <a key={t} href={abs(`/${SLUG[t]}`)}
            className="card block p-3 min-h-[44px] text-[13.5px] font-semibold leading-snug
                       transition-opacity hover:opacity-90"
            style={{ color: 'var(--series-cost)' }}>{LABEL[t]} &rarr;</a>
        ))}
      </div>
      <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-muted)' }}>
        Every analysis this project has written, in one index, is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/reports')}>reports</a>.
      </p>
    </div>
  )
}

/* ---- loading ------------------------------------------------------------- */

/** Load one payload, and render nothing rather than something stale if it is missing. */
export function useReport<T>(file: string) {
  const [d, setD] = useState<T | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    fetch(`/data/${file}`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j as T) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [file])
  return { d, err }
}

/* ---- the shell ----------------------------------------------------------- */

/** Print / Save as PDF.
 *
 *  `window.print()` and nothing else. The browser already renders this page perfectly and
 *  already knows the reader's paper size, their margins and their printer; a server-side
 *  renderer would have to be told all three and would then be producing a SECOND document
 *  that can disagree with the first. The print stylesheet in index.css is what makes the
 *  output worth having.
 *
 *  Hidden from print itself -- a button on paper is a button nobody can press. */
export function PrintButton({ label = 'Print / Save as PDF' }: { label?: string }) {
  return (
    <button type="button" onClick={() => window.print()}
      className="no-print inline-flex items-center gap-1.5 text-xs font-semibold
                 px-2.5 py-1.5 rounded border min-h-[32px] shrink-0
                 transition-opacity hover:opacity-80"
      style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)',
               background: 'var(--surface-1)' }}>
      <span aria-hidden="true">&#x2399;</span>{label}
    </button>
  )
}

/** The frame every report is drawn in.
 *
 *  `kicker` is the area or family the report belongs to, `title` is the report, and
 *  `standfirst` is ONE line under it -- rule 7a: if the standfirst needs three sentences
 *  the page is doing two jobs. `dataUrl`, where a report has one, is the published payload
 *  the page is computed from, and it is named in the error so a reader who hits a missing
 *  file still gets the rows.
 *
 *  `sourceUrl` is the report's own document where one exists -- the Markdown analyses keep
 *  theirs at /docs/analyses/<id>.md, which is rule 12's third leg. */
export function ReportShell({
  tab, kicker, title, standfirst, err, loading, dataUrl, sourceUrl, meta, children,
  noPrint,
}: {
  title: React.ReactNode
  /** A page that is an instrument rather than a document -- the search box -- has
   *  nothing to print. */
  noPrint?: boolean
  /** The page's own tab. The kicker is derived from the area it belongs to, so it cannot
   *  go stale the way six hand-typed ones had: they still read `The money` after those
   *  reports moved into the Analyses area. Rule 2 applied to a word rather than a figure. */
  tab?: Tab
  kicker?: React.ReactNode
  standfirst?: React.ReactNode
  err?: string | null
  loading?: boolean
  dataUrl?: string
  sourceUrl?: string
  meta?: React.ReactNode
  children?: React.ReactNode
}) {
  const area = tab ? areaOf(tab) : null
  const eyebrow = kicker ?? (area ? AREA_LABEL[area] : null)
  return (
    <article className="report mx-auto max-w-6xl px-5 pt-14 pb-16">
      <header className="report-head">
        {/* THE PRINT BUTTON SITS ON THE EYEBROW LINE, NOT BESIDE THE TITLE. It used to
            share a flex row with the h1, which gave the title the container minus the
            button and then capped it again at max-w-3xl -- a two-line title on every
            report. TJ: "squished". The title now runs the width of the page. */}
        <div className="flex items-start justify-between gap-4 mb-3 min-h-[1.5rem]">
          {eyebrow ? (
            <p className="text-xs font-semibold uppercase tracking-widest pt-1.5"
              style={{ color: 'var(--text-muted)' }}>{eyebrow}</p>
          ) : <span />}
          {!noPrint && <PrintButton />}
        </div>
        {/* ONE h1 treatment for every report on the site. Some titles are the report's
            NAME and some are the finding itself, in a sentence -- both are the first
            thing on the page and both are set the same, because a reader takes a
            difference in setting for a difference in weight. */}
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-5xl">{title}</h1>
        {standfirst && (
          <p className="mt-5 text-lg leading-relaxed max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>{standfirst}</p>
        )}
        {meta}
        {/* Printed only. On screen the address bar says where this came from; on paper
            nothing does, and a printout with no address is a page nobody can get back to.
            Rule 12 applied to the report itself rather than to its sources. */}
        <p className="print-only report-address">
          lunenburgbudgetproject.org &mdash; written by the Lunenburg Budget Project, an
          independent tool for residents. Not affiliated with the Town of Lunenburg, the
          School Committee or the school district.
          {sourceUrl ? ` The document this page renders: ${sourceUrl}` : ''}
          {dataUrl ? ` The data this page is computed from: ${dataUrl}` : ''}
        </p>
      </header>

      {err && (
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This report did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale.
            {dataUrl ? <> The underlying rows are published at{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(dataUrl)}>{dataUrl}</a>.</> : null}
          </p>
        </div>
      )}
      {loading && !err && (
        <p className="mt-6 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      )}
      {children}
    </article>
  )
}

/** The name the shell went by while it was only the four special education reports.
 *  Kept as an alias so those pages read the same as every other report page. */
export const Shell = ReportShell
