import type { ReactNode } from 'react'
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
export function Room({ n, tag, handsOn, title, corrects, children, leave }: {
  n: number; tag: string; handsOn?: boolean
  title: ReactNode
  /** The belief this room exists to dislodge. */
  corrects?: ReactNode
  children: ReactNode
  /** The one sentence a visitor carries out. */
  leave: ReactNode
}) {
  return (
    <section id={`room-${n}`} className="scroll-mt-32 lg:scroll-mt-16 border-t py-12"
      style={{ borderColor: 'var(--grid)' }}>
      <div className="mx-auto max-w-6xl px-5 lg:grid lg:grid-cols-[132px_1fr] lg:gap-10">
        <div className="flex items-baseline gap-3 lg:block mb-4 lg:mb-0">
          <p className="text-3xl font-bold tnum leading-none"
            style={{ color: 'var(--series-cost)' }}>
            {String(n).padStart(2, '0')}
          </p>
          <p className="text-[10px] font-semibold uppercase tracking-widest lg:mt-2.5"
            style={{ color: 'var(--text-muted)' }}>{tag}</p>
        </div>

        <div className="min-w-0">
          {/* Above the title rather than in the rail. A small tag beside a room number is
              read as a category; a filled one over the heading is read as an instruction,
              and these three rooms are the ones people should not scroll past. */}
          {handsOn && (
            <p className="inline-flex items-center gap-2 mb-3 px-3 py-1.5 rounded-md
                          text-[11px] font-bold uppercase tracking-widest"
              style={{ background: 'var(--series-cost)', color: '#fff' }}>
              <span aria-hidden="true" className="text-[13px] leading-none">&#9758;</span>
              Hands on &mdash; try this one yourself
            </p>
          )}
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight leading-[1.15] mb-3
                         max-w-3xl">{title}</h2>
          {corrects && (
            <p className="text-[13px] leading-relaxed pl-3.5 mb-5 max-w-2xl"
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
      </div>
    </section>
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
  figures: { v: string; k: string; tone?: 'critical' | 'good' }[]
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
              style={{ color: 'var(--text-secondary)' }}>{f.k}</p>
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
        <p className="text-[15px] font-bold">What last year&rsquo;s budget already cut</p>
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
        asked for and never funded &mdash; a cut by another name. This is the FY27 cycle
        only; earlier years are not in this model.
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
