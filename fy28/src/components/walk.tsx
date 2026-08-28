import { Cite } from './Citations'
import { useEffect, useState, type ReactNode } from 'react'
import { usd } from '../model/engine'
import { ALREADY_CUT, ONE_TIME_ANSWERS, SPREAD } from '../model/walk'
import { MODEL, usdShort } from '../model/engine'
import { DEVELOPMENT, FEASIBILITY } from '../model/answers'

/** The exhibit's structural language, as components.
 *
 *  The design this came from is a museum wall, and almost all of what made it readable was
 *  structure rather than decoration: a numbered rail so you know where you are in a
 *  sequence, one belief named as the thing the room corrects, the object in the middle, and
 *  a single sentence to leave with. Typography and palette stay the site's own — a page
 *  that changed typeface halfway through the site would read as a different product, and
 *  the charts have to sit inside it. */

/** One room. Everything about it is singular on purpose: one belief, one object, one
 *  sentence out. If a room needs two of any of those it is two rooms. */
export function Room({ n, slug, tag, handsOn, title, corrects, children, leave }: {
  n: number
  /** The room's address, and the thing a shared link actually points at.
   *
   *  Named rather than numbered because the number is a position in a sequence and the
   *  sequence has already changed once. Insert a room and every link anybody has sent
   *  since starts opening the room next door — which is the failure mode a permanent URL
   *  exists to prevent. `room-N` is kept alive below as an alias for links already out
   *  there, and never generated again. */
  slug: string
  tag: string; handsOn?: boolean
  title: ReactNode
  /** The belief this room exists to dislodge. */
  corrects?: ReactNode
  children: ReactNode
  /** The one sentence a visitor carries out. */
  leave: ReactNode
}) {
  return (
    <section id={slug} className="scroll-mt-12 border-t"
      style={{ borderColor: 'var(--grid)' }}>
      {/* The old numbered anchor, kept working. A link that has been shared once is out
          of your hands forever. */}
      <span id={`room-${n}`} aria-hidden="true" className="block scroll-mt-12" />
      {/* The heading stays put for as long as you are in the room.
       *
       * Rooms are long — several carry a whole chart — and a reader who scrolls into the
       * middle of one has no way of telling which of eleven they are in or what question
       * it was answering. Sticky inside the section rather than on the page, so it
       * releases at the room boundary and the next room's heading takes over: the
       * behavior of a wall label you walk past, which is the thing this imitates.
       *
       * In a hands-on room only the identity strip stays. Three sticky layers were
       * stacking there — site header, room heading, pinned chart — and a two-line title
       * is the least useful of the three to a reader who is trying to drag a slider and
       * watch a curve at the same time. You already know which room you are in; what you
       * need on screen is the thing that moves when you move something. The strip keeps
       * the orientation and gives the chart back its fifty pixels. */}
      <div className={`sticky top-12 z-10 backdrop-blur border-b`}
        style={{ background: 'color-mix(in srgb, var(--surface-2) 93%, transparent)',
                 borderColor: 'var(--grid)' }}>
        <div className="mx-auto max-w-6xl px-5 py-2.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="text-[13px] font-bold tnum leading-none"
              style={{ color: 'var(--series-cost)' }}>{String(n).padStart(2, '0')}</span>
            <span className="text-[10px] font-semibold uppercase tracking-widest leading-none"
              style={{ color: 'var(--text-muted)' }}>{tag}</span>
            {handsOn && (
              <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1
                               rounded leading-none"
                style={{ background: 'var(--series-cost)', color: '#fff' }}>
                <span aria-hidden="true" className="mr-1">&#9758;</span>
                Hands on
              </span>
            )}
            <SectionLink id={slug} what={`room ${n}`} />
          </div>
          {!handsOn && (
            <h2 className="text-[17px] sm:text-2xl font-bold tracking-tight leading-snug
                           mt-1 line-clamp-2">{title}</h2>
          )}
        </div>
      </div>

      {/* Reading rooms get the generous vertical rhythm; hands-on rooms get their
          controls on screen. Thirty-six pixels of breathing room above and below is right
          for a page you read and is just distance to scroll on a page you operate. */}
      <div className={`mx-auto max-w-6xl px-5 ${handsOn ? 'pt-5 pb-7' : 'py-9'}`}>
        {handsOn && (
          <h2 className="text-[19px] sm:text-2xl font-bold tracking-tight leading-snug
                         mb-3 max-w-3xl">{title}</h2>
        )}
        {corrects && (
          <p className="text-[13px] leading-relaxed pl-3.5 mb-4 max-w-2xl"
            style={{ borderLeft: '2px solid var(--status-critical)',
                     color: 'var(--text-secondary)' }}>
            <span className="block text-[10px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--status-critical)' }}>Corrects</span>
            {corrects}
          </p>
        )}
        <div className="space-y-4">{children}</div>
        <div className="card p-4 sm:p-5 mt-6 max-w-3xl">
          <p className="text-[10px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>You leave knowing</p>
          <p className="text-[17px] leading-snug font-medium">{leave}</p>
        </div>
      </div>
    </section>
  )
}

/** A permanent address for one section, offered rather than hidden.
 *
 *  Every room on this page has been quietly linkable the whole time and nothing said so,
 *  which means the only people who could share a particular argument were the ones who
 *  thought to read the DOM. This site is written to be quoted at a meeting — "the part
 *  about what an override actually buys" should be a link somebody can send, not an
 *  instruction to scroll.
 *
 *  Copies the absolute URL and updates the address bar, so the browser's own share and
 *  bookmark controls agree with what was copied. `replaceState` rather than `pushState`:
 *  collecting a history entry per heading would turn the back button into a tour of the
 *  headings somebody clicked. */
export function SectionLink({ id, what }: { id: string; what: string }) {
  const [said, setSaid] = useState<'copied' | 'linked' | null>(null)

  useEffect(() => {
    if (!said) return
    const t = setTimeout(() => setSaid(null), 1900)
    return () => clearTimeout(t)
  }, [said])

  const onClick = (e: React.MouseEvent) => {
    // Modified clicks are the reader opening it in a new tab, which already works.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    e.preventDefault()
    const here = `${window.location.pathname}#${id}`
    window.history.replaceState(null, '', here)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
    // Clipboard access fails on insecure origins and wherever permission is refused. The
    // link still works — the address bar has it — so say which of the two happened.
    navigator.clipboard?.writeText(window.location.origin + here)
      .then(() => setSaid('copied'), () => setSaid('linked')) ?? setSaid('linked')
  }

  return (
    <a href={`#${id}`} onClick={onClick}
      aria-label={`Copy a link to ${what}`}
      className="ml-auto flex items-center gap-1 text-[10px] font-semibold uppercase
                 tracking-widest leading-none shrink-0 opacity-60 hover:opacity-100
                 focus-visible:opacity-100 transition-opacity"
      style={{ color: said ? 'var(--status-good)' : 'var(--text-muted)' }}>
      <span aria-hidden="true">#</span>
      <span aria-live="polite">
        {said === 'copied' ? 'Copied' : said === 'linked' ? 'In the bar' : 'Link'}
      </span>
    </a>
  )
}

/** Body copy inside a room. Sized for reading rather than for scanning. */
export const Say = ({ children }: { children: ReactNode }) => (
  <p className="text-[15px] leading-relaxed max-w-2xl"
    style={{ color: 'var(--text-secondary)' }}>{children}</p>
)

/** The object on the wall: a few figures, captioned, nothing else. */
export function Plate({ label, figures }: {
  label: string
  figures: { v: string; k: string; tone?: 'critical' | 'good'; cite?: string }[]
}) {
  return (
    <div className="card p-4 sm:p-5">
      <p className="text-[10px] font-bold uppercase tracking-widest mb-4"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <div className="flex flex-wrap gap-x-10 gap-y-6">
        {figures.map(f => (
          <div key={f.k} className="min-w-[120px]">
            <p className="text-2xl font-bold tnum leading-none" style={{
              color: f.tone === 'critical' ? 'var(--status-critical)'
                : f.tone === 'good' ? 'var(--status-good)' : 'var(--text-primary)' }}>
              {f.v}
            </p>
            <p className="text-xs mt-2 leading-snug max-w-[26ch]"
              style={{ color: 'var(--text-secondary)' }}>
              {f.k}{f.cite && <Cite id={f.cite} />}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

/** What the town has already given up, named.
 *
 *  Nine positions read as a statistic. "Two classroom teachers, Primary School" does not,
 *  and the difference decides whether the next four rooms get a hearing. */
export function AlreadyCut() {
  return (
    <div className="card p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3 mb-1">
        <p className="text-[15px] font-bold">What this year&rsquo;s budget already cut</p>
        <p className="text-[13px] tnum font-semibold" style={{ color: 'var(--status-critical)' }}>
          {ALREADY_CUT.fte} FTE &middot; {usd(ALREADY_CUT.cost)}
        </p>
      </div>
      <p className="text-[12px] mb-3" style={{ color: 'var(--text-secondary)' }}>
        {ALREADY_CUT.count} lines in all. These are the ones that were somebody&rsquo;s job.
      </p>
      <ul className="rounded-lg overflow-hidden" style={{ background: 'var(--surface-3)' }}>
        {ALREADY_CUT.people.map((p, i) => (
          <li key={p.id} className="flex items-baseline justify-between gap-3 px-3 py-2"
            style={i ? { borderTop: '1px solid var(--grid)' } : undefined}>
            <span className="text-[13px] leading-snug min-w-0">{p.label}</span>
            <span className="text-[12px] tnum shrink-0" style={{ color: 'var(--text-secondary)' }}>
              {p.fte.toFixed(1)} FTE
            </span>
          </li>
        ))}
      </ul>
      <p className="text-[12px] mt-3" style={{ color: 'var(--text-muted)' }}>
        A further {ALREADY_CUT.unfunded.fte} FTE and {usd(ALREADY_CUT.unfunded.cost)} was
        asked for and never funded &mdash; a cut by another name. This is the FY27 budget
        the town is running on now; earlier years are not in this model.
      </p>
    </div>
  )
}

/** Every answer anybody has proposed, priced the same way, with the only two columns that
 *  decide anything. The column of zeros is the argument. */
export function OneTimeAnswers() {
  return (
    <div className="card p-4">
      <table className="stack w-full text-[13px] tnum">
        <caption className="sr-only">
          Each proposed answer, what it is worth next year, how many years it funds, and its
          effect on the growth rate
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">What you do</th>
            <th className="font-semibold py-1.5 text-right">Worth</th>
            <th className="font-semibold py-1.5 text-right">Years it funds</th>
            <th className="font-semibold py-1.5 text-right">Effect on the rate</th>
          </tr>
        </thead>
        <tbody>
          {ONE_TIME_ANSWERS.map(r => (
            <tr key={r.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-2 font-semibold">{r.label}</td>
              <td data-label="Worth" className="py-2 text-right">{usd(r.amount)}</td>
              <td data-label="Years it funds" className="py-2 text-right"
                style={{ color: r.years === 0 ? 'var(--status-critical)' : undefined }}>
                {r.years === null ? '—' : r.years}
              </td>
              <td data-label="Effect on the rate" className="py-2 text-right font-semibold"
                style={{ color: r.points ? 'var(--status-good)' : 'var(--status-critical)' }}>
                {r.points
                  ? `${(r.points * 100).toFixed(2)} of ${(SPREAD * 100).toFixed(2)} points`
                  : 'none'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[12px] mt-3 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        The last column is the whole page. Everything the town actually argues about sits in
        the rows that say <strong>none</strong>, and the two rows that change anything are
        the two nobody is arguing about.
      </p>
    </div>
  )
}

/** What a "development" is, because otherwise the count is meaningless.
 *
 *  "27 developments a year" is a number without a unit: a reader cannot tell whether that
 *  is a strip mall or a shed, and the honest answer changes the argument completely. The
 *  model's unit is a $3M mixed archetype, and unpacking it into actual buildings produces
 *  the scale fact this room needs — 228 buildings in five years against the 234 commercial
 *  properties the town has managed to accumulate in its entire history. */
export function WhatIsADevelopment() {
  const mix = MODEL.taxBase.archetypes.find(a => a.id === 'mix')!
  const T = MODEL.taxBase
  return (
    <div className="card p-4 sm:p-5">
      <p className="text-[15px] font-bold">What one &ldquo;development&rdquo; means here</p>
      <p className="text-[13px] mt-1 mb-3" style={{ color: 'var(--text-secondary)' }}>
        The model&rsquo;s unit is <strong>{usd(mix.value)}</strong> of new assessed value
        &mdash; a mix, not one building type, because that is what actually gets built. So{' '}
        {DEVELOPMENT.fiveYear.developments.toFixed(0)} a year is, in real buildings:
      </p>
      <ul className="rounded-lg overflow-hidden" style={{ background: 'var(--surface-3)' }}>
        {FEASIBILITY.each.slice().sort((a, b) => b.perYear - a.perYear).map((e, i) => (
          <li key={e.label} className="flex items-baseline justify-between gap-3 px-3 py-2"
            style={i ? { borderTop: '1px solid var(--grid)' } : undefined}>
            <span className="text-[13px] leading-snug min-w-0">
              {e.label}
              <span className="ml-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                {usd(e.unit)} each
              </span>
            </span>
            <span className="text-[13px] font-semibold tnum shrink-0">
              {e.perYear.toFixed(1)}<span className="font-normal text-[11px]"> a year</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="text-[13px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <strong>That is {FEASIBILITY.buildings5} new commercial buildings over five
        years.</strong> Lunenburg has {T.businesses} commercial properties today, worth{' '}
        {usdShort(T.fy23.cipValue)} in total &mdash; accumulated over the whole life of the
        town. This asks for very nearly that many again, in five years, one every{' '}
        {FEASIBILITY.everyDays} days.
      </p>
      <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
        It would take commercial property from{' '}
        {(FEASIBILITY.businessShareNow * 100).toFixed(0)}% of the town&rsquo;s value to{' '}
        {(FEASIBILITY.businessShareAfter * 100).toFixed(0)}%. And it has somewhere to go
        or it does not happen: {MODEL.taxBase.commercialContext.constraint.toLowerCase()}
      </p>
    </div>
  )
}
