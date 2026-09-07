import { useEffect, useState } from 'react'
import type { Tab } from '../routes'

/** What we cannot answer — the gaps, in one place, with what would close each of them.
 *
 *  WHY THIS PAGE EXISTS, AND WHY IT IS NOT A DISCLAIMER
 *
 *  Three separate bodies of material said "we cannot answer this" and none of them was
 *  reachable by a resident. `money_gaps` was a section at the bottom of /the-money;
 *  `notes/reference/EXTRACTION-GAPS.md` was generated, checked, and published nowhere at
 *  all; `notes/generated/DATA-REQUEST.md` is a letter to the Town that only its recipient
 *  ever saw. They are three different kinds of gap and the difference between them is the
 *  useful part, so they are grouped rather than merged:
 *
 *    1. WHAT NO DOCUMENT SAYS      the records exist, they are held, and they do not
 *                                  contain the answer. `money_gaps`.
 *    2. WHAT WE HOLD AND HAVE NOT  extracted from the annual reports and never recomputed
 *       CHECKED                    against a total the report itself prints — plus four
 *                                  table families surveyed in every report and never
 *                                  extracted at all.
 *    3. WHAT WE ASKED FOR AND      report-years the Town can produce and has not sent.
 *       HAVE NOT RECEIVED          This is the half that is somebody's to fix.
 *    4. WHAT THE MODEL ASSUMES     `money_assumptions` — an inference the analysis rests
 *                                  on, with what would settle it.
 *
 *  Each carries the document that would close it wherever one is known. That column is the
 *  point of the page: a gap with a named document is a piece of work somebody can do, and
 *  a gap without one is a statement about what the town publishes.
 *
 *  NOT ONE FIGURE IS TYPED HERE (CLAUDE.md rule 2). Everything arrives at runtime from
 *  four generated static files — no D1 read budget is spent by opening this page:
 *
 *    /api/money_gaps.json         the `money_gaps` table, published whole by build_api.py
 *    /api/money_assumptions.json  the `money_assumptions` table, likewise
 *    /data/extraction-gaps.json   written by scripts/build_extraction_gaps.py, alongside
 *                                 the Markdown it has always written. The arithmetic lives
 *                                 THERE and not here: two implementations of one count are
 *                                 two counts, and they disagree the day one is edited.
 *    /data/data-request.json      written by scripts/build_request_doc.py from the coverage
 *                                 matrix, alongside the letter.
 *
 *  RULE 7a: THE PAGE OPENS WITH THE GAPS. Not with an explanation of what a gap is, not
 *  with the method, not with a caveat about how to read the table. The first thing under
 *  the title is the list. What each group means is said on the group, where a reader meets
 *  it after seeing what it describes.
 *
 *  RULE 7 GOVERNS EVERY SENTENCE ON IT. What is stated is what the records do or do not
 *  contain. Nothing here says why a document is missing, and nothing here treats a gap as
 *  a finding about anybody — see notes/HANDOFF-MONEY-IN.md, "Claims NOT established".
 *
 *  A FILTER THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT, so every list on
 *  this page says so out loud rather than rendering as empty space. On a page about gaps
 *  that is not a nicety: an empty gap list reads as "no gaps", which is the one thing this
 *  page must never say wrongly. */

type Gap = { side: string; what: string; why: string }
type GapIndex = { count: number; rows: Gap[] }

type Assumption = { assumption: string; evidence: string; rests_on: string; settled_by: string }
type AssumptionIndex = { count: number; rows: Assumption[] }

type Extraction = {
  checked: number; checkFailed: number; noCheck: number; rows: number
  datasets: { dataset: string; checked: number; checkFailed: number; noCheck: number
    nothingChecked: boolean }[]
  neverExtracted: { family: string; years: number; figureRows: number
    whyItMatters: string | null }[]
  neverExtractedRows: number
  catalogued: number; readIntoADataset: number
  byDifficulty: { judgement: string; tables: number; rows: number }[]
}

type Request = {
  years: number[]; outstanding: number; reportYears: number; received: number
  rows: { fy: number; report: string; why: string; status: string; publisher: string
    howToGet: string }[]
  alreadyReceived: { fy: number; report: string }[]
  reports: { report: string; why: string }[]
  fundsNotHeld: { fund: string; name: string }[]
}

const n = (x: number) => x.toLocaleString()

/** The gap text carries `**bold**` and `` `code` `` from the CSVs the town's own records
 *  were transcribed into. Rendered rather than stripped: the emphasis is the author's and
 *  it lands on the load-bearing half of the sentence, and a backtick around an account
 *  name is the difference between a word and an identifier. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i}>{part.slice(2, -2)}</strong>
        }
        if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
          return <code key={i} className="text-[0.92em]">{part.slice(1, -1)}</code>
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold tracking-tight mt-16 mb-3 max-w-3xl">{children}</h2>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-widest mb-2.5"
      style={{ color: 'var(--text-muted)' }}>{children}</p>
  )
}

/** One gap. A rule down the left rather than a card, because a card is what a LINK looks
 *  like on the money pages and none of these go anywhere. */
function GapItem({ head, body, foot }: { head: string; body: string; foot?: string }) {
  return (
    <li className="pl-3.5 py-1" style={{ borderLeft: '2px solid var(--grid)' }}>
      <p className="text-[14.5px] font-bold leading-snug"><Rich text={head} /></p>
      <p className="text-[13px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
        <Rich text={body} />
      </p>
      {foot && (
        <p className="text-[12.5px] leading-snug mt-1.5" style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold uppercase tracking-wider text-[10.5px]">
            would close it&nbsp;&middot;&nbsp;</span>
          <Rich text={foot} />
        </p>
      )}
    </li>
  )
}

/** Said out loud, in warning colour, wherever a list came back empty. */
function Missing({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[13.5px] mt-4 max-w-2xl" style={{ color: 'var(--status-warning)' }}>
      {children}
    </p>
  )
}

/** A figure with its label. The four across the top of the extraction section are the
 *  headline of that section, so they are numbers first and words second. */
function Metric({ value, label, warn }: { value: string; label: string; warn?: boolean }) {
  return (
    <div className="card px-4 py-3">
      <p className="text-[22px] font-bold leading-none tnum"
        style={{ color: warn ? 'var(--status-warning)' : 'var(--text-primary)' }}>{value}</p>
      <p className="text-[11.5px] mt-1.5 leading-snug" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
    </div>
  )
}

/** `money_gaps` uses `money_in` / `money_out` / `document_wanted`. Read off the value
 *  rather than mapped through a table typed here, so a fourth kind of gap appears on this
 *  page the day it appears in the data. */
const sideLabel = (s: string) => s.replace(/_/g, ' ')

/** The `document_wanted` rows carry two halves in one field: what the document is, and
 *  what holding it would close. Split for display only — if the separator is ever absent
 *  the whole string is shown rather than half of it. */
function splitCloses(why: string): [string, string | undefined] {
  const i = why.indexOf(' — closes: ')
  return i < 0 ? [why, undefined] : [why.slice(0, i), why.slice(i + ' — closes: '.length)]
}

export function Gaps({ onJump }: { onJump: (t: Tab) => void }) {
  const [gaps, setGaps] = useState<GapIndex | null>(null)
  const [ext, setExt] = useState<Extraction | null>(null)
  const [req, setReq] = useState<Request | null>(null)
  const [ass, setAss] = useState<AssumptionIndex | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    const get = (u: string) =>
      fetch(u).then(r => (r.ok ? r.json() : Promise.reject(new Error(`${u}: HTTP ${r.status}`))))
    Promise.all([get('/api/money_gaps.json'), get('/data/extraction-gaps.json'),
      get('/data/data-request.json'), get('/api/money_assumptions.json')])
      .then(([g, e, r, a]) => {
        if (!live) return
        setGaps(g); setExt(e); setReq(r); setAss(a)
      })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const rows = gaps?.rows ?? []
  const wanted = rows.filter(g => g.side === 'document_wanted')
  const unanswered = rows.filter(g => g.side !== 'document_wanted')
  const sides = [...new Set(unanswered.map(g => g.side))]
  const byYear = [...new Set((req?.rows ?? []).map(r => r.fy))].sort()

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        What we cannot answer
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Every question below is one this project went looking for and could not settle from
        the published records &mdash; and, where one is known, the single document that
        would.
      </p>

      {err && (
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This page&rsquo;s data did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. The lists themselves are still at <code>/api/money_gaps.json</code>,{' '}
            <code>/data/extraction-gaps.json</code>, <code>/data/data-request.json</code>{' '}
            and <code>/api/money_assumptions.json</code>.
          </p>
        </div>
      )}

      {/* 1 -------------------------------------------------------------- money_gaps */}
      <H2>What no document says</H2>
      <div className="mt-6 grid gap-8 sm:grid-cols-2">
        {sides.map(side => (
          <div key={side}>
            <Eyebrow>{sideLabel(side)}</Eyebrow>
            <ul className="space-y-2.5">
              {unanswered.filter(g => g.side === side).map(g => (
                <GapItem key={g.what} head={g.what} body={g.why} />
              ))}
            </ul>
          </div>
        ))}
      </div>
      <Body>
        These are held records that do not contain the answer. The town publishes a great
        deal; what it does not publish is the mapping &mdash; which fund pays which post,
        which project a transfer bought, which share of a pooled assessment is the
        school&rsquo;s. A budget line is what the town must <em>raise</em> after everything
        else has paid its share, and nothing on the page marks what that was.
      </Body>
      {gaps && !unanswered.length && (
        <Missing>
          <code>/api/money_gaps.json</code> answered with no unanswered-question rows. That
          is the endpoint changing shape, not the archive answering everything.
        </Missing>
      )}

      {wanted.length > 0 && (
        <>
          <p className="text-[11px] font-semibold uppercase tracking-widest mt-12 mb-3"
            style={{ color: 'var(--text-muted)' }}>The documents that would close these</p>
          <ul className="space-y-3">
            {wanted.map(g => {
              const [what, closes] = splitCloses(g.why)
              return <GapItem key={g.what} head={g.what} body={what} foot={closes} />
            })}
          </ul>
          <p className="text-xs leading-relaxed mt-5" style={{ color: 'var(--text-muted)' }}>
            {n(gaps!.count)} entries in total, published as{' '}
            <a href="/api/money_gaps.json" className="underline"
              style={{ color: 'var(--text-secondary)' }}><code>/api/money_gaps.json</code></a>{' '}
            and queryable as <code>money_gaps</code>. Each is something we went looking for
            and could not establish &mdash; not a claim about anybody.
          </p>
        </>
      )}

      {/* 2 ------------------------------------------------------- extraction gaps */}
      <H2>What we hold, and have not checked</H2>
      <Body>
        Sixteen annual town reports were read page by page into datasets.{' '}
        <strong>Checked</strong> means the extract was recomputed against a total the
        report itself prints and agreed with it. Most of it has not been.
      </Body>
      {ext && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-6">
            <Metric value={n(ext.checked)} label="rows checked against a printed total" />
            <Metric value={n(ext.checkFailed)} warn
              label="rows whose columns do not sum to the total the report prints" />
            <Metric value={n(ext.noCheck)}
              label="rows from a table that prints no total to check against" />
            <Metric value={n(ext.rows)} label="extracted rows in all" />
          </div>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-[13px] tnum" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left font-semibold py-2 pr-3">dataset</th>
                  <th className="text-right font-semibold py-2 px-2">checked</th>
                  <th className="text-right font-semibold py-2 px-2">check failed</th>
                  <th className="text-right font-semibold py-2 pl-2">no check</th>
                </tr>
              </thead>
              <tbody>
                {ext.datasets.map(d => (
                  <tr key={d.dataset} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-2 pr-3">
                      <code className="text-[12.5px]">{d.dataset}</code>
                      {d.nothingChecked && (
                        <span className="ml-1.5 text-[11px] font-semibold"
                          style={{ color: 'var(--status-warning)' }}
                          title="nothing in this dataset is checked">&#9888;</span>
                      )}
                    </td>
                    <td className="text-right py-2 px-2">{n(d.checked)}</td>
                    <td className="text-right py-2 px-2">{n(d.checkFailed)}</td>
                    <td className="text-right py-2 pl-2">{n(d.noCheck)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs leading-relaxed mt-3" style={{ color: 'var(--text-muted)' }}>
            &#9888; marks a dataset where <strong>nothing</strong> is checked. A failed check
            is usually a property of the instrument rather than of the data: the special
            revenue schedule carried a failing label from the day it was extracted, and
            reconciled to the penny the first time somebody put the extract next to the
            page it came from.
          </p>

          <p className="text-[11px] font-semibold uppercase tracking-widest mt-12 mb-3"
            style={{ color: 'var(--text-muted)' }}>
            In every report, and never extracted at all
          </p>
          <ul className="space-y-3">
            {ext.neverExtracted.map(f => (
              <GapItem key={f.family}
                head={`\`${f.family}\` — ${f.years} years, ${n(f.figureRows)} figure rows`}
                body={f.whyItMatters ?? 'Surveyed in the reports; no dataset holds it.'} />
            ))}
          </ul>
          <Body>
            {n(ext.neverExtractedRows)} figure rows in all, counted by reading the reports
            and never read into anything. The wider survey catalogued {n(ext.catalogued)}{' '}
            tables in those reports; {n(ext.readIntoADataset)} have been read into a
            dataset. The difference is not all loss &mdash; a catalogue entry can be the
            same table on another page, or prose &mdash; and it is not nothing either.
          </Body>
          {!ext.neverExtracted.length && (
            <Missing>
              <code>/data/extraction-gaps.json</code> lists no never-extracted family. That
              is a broken join, not a finished archive.
            </Missing>
          )}
        </>
      )}
      {!ext && !err && <Body>Loading the extraction counts&hellip;</Body>}

      {/* 3 ---------------------------------------------------------- the data request */}
      <H2>What we have asked for, and not received</H2>
      {req && (
        <>
          <Body>
            <strong>{n(req.outstanding)} of {n(req.reportYears)}</strong> report-years are
            outstanding for FY{req.years[0]}&ndash;FY{req.years[req.years.length - 1]}.
            Every one is a report the Town can run out of MUNIS; {n(req.received)} have
            arrived and are not asked for again. This list is computed from what the
            archive holds, so a document that arrives leaves it.
          </Body>
          {byYear.map(fy => (
            <div key={fy} className="mt-8">
              <Eyebrow>FY{fy}</Eyebrow>
              <ul className="space-y-2.5">
                {req.rows.filter(r => r.fy === fy).map(r => (
                  <li key={r.report} className="pl-3.5 py-1"
                    style={{ borderLeft: '2px solid var(--grid)' }}>
                    <p className="text-[14.5px] font-bold leading-snug">
                      {r.report}
                      {r.status !== 'missing' && (
                        <span className="ml-2 text-[10.5px] font-semibold uppercase
                                         tracking-wider"
                          style={{ color: 'var(--status-warning)' }}>{r.status}</span>
                      )}
                    </p>
                    <p className="text-[13px] leading-snug mt-1"
                      style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {!req.rows.length && (
            <Missing>
              <code>/data/data-request.json</code> lists nothing outstanding. Check the
              coverage matrix before reading that as everything having arrived.
            </Missing>
          )}

          {req.fundsNotHeld.length > 0 && (
            <>
              <p className="text-[11px] font-semibold uppercase tracking-widest mt-12 mb-2.5"
                style={{ color: 'var(--text-muted)' }}>
                The single ask that closes the most
              </p>
              <Body>
                Everything received so far is Fund 0100 &mdash; the town&rsquo;s share and
                nothing else. These are the funds that spent money on the schools in FY26
                and cannot be attached to any budget line. The simplest form of the ask is
                the same report with the fund criterion left blank.
              </Body>
              <div className="mt-4 flex flex-wrap gap-2">
                {req.fundsNotHeld.map(f => (
                  <span key={f.fund} className="card px-3 py-2 text-[12.5px] leading-snug">
                    <code className="tnum font-semibold">{f.fund}</code>
                    {f.name && <span style={{ color: 'var(--text-secondary)' }}> {f.name}</span>}
                  </span>
                ))}
              </div>
            </>
          )}

          {req.alreadyReceived.length > 0 && (
            <>
              <p className="text-[11px] font-semibold uppercase tracking-widest mt-12 mb-2.5"
                style={{ color: 'var(--text-muted)' }}>
                Already received &mdash; not asked for again
              </p>
              <ul className="text-[13.5px] leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}>
                {req.alreadyReceived.map(r => (
                  <li key={`${r.fy}-${r.report}`}>FY{r.fy} &mdash; {r.report}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      {!req && !err && <Body>Loading the outstanding request&hellip;</Body>}

      {/* 4 ------------------------------------------------------------- assumptions */}
      <H2>What the model assumes, because nothing settles it</H2>
      <Body>
        Where a route could not be traced and the analysis still had to say something, it
        says it as an assumption and names what would test it. These are inferences, not
        measurements.
      </Body>
      <div className="mt-6 grid gap-2.5">
        {(ass?.rows ?? []).map(a => (
          <div key={a.assumption} className="card px-4 py-4">
            <p className="text-[15px] font-bold leading-snug"><Rich text={a.assumption} /></p>
            <p className="text-[13px] leading-snug mt-1.5"
              style={{ color: 'var(--text-secondary)' }}>
              <span className="font-semibold uppercase tracking-wider text-[10.5px]"
                style={{ color: 'var(--text-muted)' }}>evidence&nbsp;&middot;&nbsp;</span>
              <Rich text={a.evidence} />
            </p>
            <p className="text-[13px] leading-snug mt-1"
              style={{ color: 'var(--text-secondary)' }}>
              <span className="font-semibold uppercase tracking-wider text-[10.5px]"
                style={{ color: 'var(--text-muted)' }}>what rests on it&nbsp;&middot;&nbsp;</span>
              <Rich text={a.rests_on} />
            </p>
            <p className="text-[13px] leading-snug mt-1">
              <span className="font-semibold uppercase tracking-wider text-[10.5px]"
                style={{ color: 'var(--text-muted)' }}>would settle it&nbsp;&middot;&nbsp;</span>
              <Rich text={a.settled_by} />
            </p>
          </div>
        ))}
      </div>
      {ass && !ass.rows.length && (
        <Missing>
          <code>/api/money_assumptions.json</code> answered with no rows. An empty
          assumption list means the endpoint changed shape, not that the model assumes
          nothing.
        </Missing>
      )}

      {/* ------------------------------------------------------------------- the files */}
      <H2>Where these lists come from</H2>
      <Body>
        Every count on this page is computed when the site is built, from the same files a
        reader can download. Nothing here is typed into a sentence.
      </Body>
      <ul className="mt-4 text-[13.5px] leading-relaxed space-y-1.5"
        style={{ color: 'var(--text-secondary)' }}>
        <li>
          <a href="/api/money_gaps.json" className="underline"
            style={{ color: 'var(--series-cost)' }}><code>/api/money_gaps.json</code></a>{' '}
          &mdash; what the published records do not answer, and the document that would.
        </li>
        <li>
          <a href="/data/extraction-gaps.json" className="underline"
            style={{ color: 'var(--series-cost)' }}><code>/data/extraction-gaps.json</code></a>{' '}
          &mdash; what has been read from the annual reports, and what has been checked.
        </li>
        <li>
          <a href="/data/data-request.json" className="underline"
            style={{ color: 'var(--series-cost)' }}><code>/data/data-request.json</code></a>{' '}
          &mdash; the report-years outstanding from the Town, recomputed from what is held.
        </li>
        <li>
          <a href="/api/money_assumptions.json" className="underline"
            style={{ color: 'var(--series-cost)' }}><code>/api/money_assumptions.json</code></a>{' '}
          &mdash; every assumption the money model rests on, with what would settle it.
        </li>
      </ul>
      <Body>
        How the money does move, where it can be followed, is the other half of this
        area &mdash;{' '}
        <button onClick={() => onJump('themoney')} className="underline"
          style={{ color: 'var(--series-cost)' }}>How the money moves</button>.
      </Body>
    </div>
  )
}
