/** THE CITIZEN-FIRST TOP OF A REPORT. A prototype of a proposed standard, used by
 *  /analysis/transportation only until TJ approves it -- notes/process/REPORT-FORMAT.md.
 *
 *  WHY IT EXISTS. Residents told TJ the report tops were hard to parse: a big number with a
 *  paragraph under it, then cards, and no sentence anybody could carry out of the room. So
 *  the unit here is the SENTENCE, and the page is ordered by DEPTH: what is going on; a
 *  verdict per question a resident asks, with the sentence to repeat; under each, what that
 *  sentence rests on, one layer deeper at a time, ending at the evidence on this page or at
 *  the document that would settle it. A reader who stops after the
 *  first screen has the whole picture. A skeptic follows one answer down without reading
 *  the others.
 *
 *  NOTHING HERE IS TYPED. Every word comes out of the payload, where scripts/brief.py has
 *  already checked that every digit is a registered figure, every sentence fits its width
 *  budget, and every link lands on a heading the document writes. */
import type React from 'react'

export type Fig = { value: number | string; text: string; unit: string }
export type Unit = { text: string; figures: Record<string, Fig>; literals: string[] }
export type StepKind = 'measured' | 'quote' | 'caption' | 'estimate' | 'hypothesis' | 'gap'
export type Step = Unit & {
  kind: StepKind
  link?: { anchor: string; label: string }
  cite?: { href: string; label: string }
  closes?: string
}
export type Verdict = 'sound' | 'concern' | 'problem' | 'unknown'
export type Chain = {
  id: string; question: string; verdict: Verdict; label: string; say: Unit; steps: Step[]
}
export type Brief = { answer: Unit; chains: Chain[] }

/* A verdict is told apart by a coloured mark AND its word, never by colour alone: the word
   carries it for a reader who cannot tell the hues apart, and in print. The hues are the
   site's status tokens, which are already set for both themes. */
/* The labels themselves come from the payload (scripts/brief.py): Matches, Mixed picture,
   Does not match, Can't tell yet -- each the result of a comparison, never a charge. */
const TONE: Record<Verdict, string> = {
  sound: 'var(--status-good)',
  concern: 'var(--status-warning)',
  problem: 'var(--status-bad)',
  unknown: 'var(--axis)',
}

/* What KIND of statement a layer is -- rule 7, said on every line rather than once in a
   method note at the bottom. */
const KIND: Record<StepKind, string> = {
  measured: 'Measured',
  quote: 'On the record',
  caption: 'From the recording — machine captions',
  estimate: 'Our estimate',
  hypothesis: 'A possible explanation — not tested',
  gap: 'Not published',
}

/** The sentence, with every figure it states set in bold -- the part a reader will say. */
function Said({ u }: { u: Unit }) {
  // Amounts and rates are what a reader repeats; a fiscal year is context, and bolding every
  // FY2026 turns the emphasis into noise.
  const texts = Object.values(u.figures).filter(f => f.unit !== 'fiscal year')
    .map(f => f.text).filter(Boolean)
    .sort((a, b) => b.length - a.length)
  if (!texts.length) return <>{u.text}</>
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const parts = u.text.split(new RegExp(`(${texts.map(esc).join('|')})`, 'g'))
  return <>{parts.map((p, i) => (texts.includes(p) ? <strong key={i}>{p}</strong> : p))}</>
}

function Tag({ v, label }: { v: Verdict; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase
                     tracking-wider whitespace-nowrap" style={{ color: 'var(--text-primary)' }}>
      <span aria-hidden="true" className="inline-block w-2.5 h-2.5 rounded-full"
        style={{ background: TONE[v] }} />
      {label}
    </span>
  )
}

const linkStyle: React.CSSProperties = { color: 'var(--series-cost)' }

function Layers({ steps }: { steps: Step[] }) {
  return (
    <ol className="mt-3 space-y-2.5">
      {steps.map((s, i) => (
        /* Each layer sits a little further in than the one it explains: the depth is drawn,
           not announced. Capped at three steps of indent so a phone keeps its measure. */
        <li key={i} className="pl-3 border-l-2"
          style={{ marginLeft: `${Math.min(i, 3) * 0.75}rem`,
                   borderColor: s.kind === 'gap' ? 'var(--status-warning)'
                     : s.kind === 'hypothesis' || s.kind === 'caption' ? 'var(--axis)'
                     : 'var(--grid)' }}>
          <p className="text-[10.5px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>{KIND[s.kind]}</p>
          <p className="text-[14.5px] leading-relaxed mt-0.5"
            style={{ color: 'var(--text-secondary)' }}>
            <Said u={s} />
          </p>
          {s.closes ? (
            <p className="text-[13px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
              <span className="font-semibold">What would settle it:</span> {s.closes}.
            </p>
          ) : null}
          {s.cite || s.link ? (
            <p className="text-[13px] mt-1 no-print">
              {s.cite ? (
                <a className="underline" style={linkStyle} href={s.cite.href}
                  target={s.cite.href.startsWith('http') ? '_blank' : undefined}
                  rel={s.cite.href.startsWith('http') ? 'noreferrer' : undefined}>
                  {s.cite.label}</a>
              ) : null}
              {s.cite && s.link ? ' · ' : null}
              {s.link ? (
                <a className="underline" style={linkStyle} href={`#${s.link.anchor}`}>
                  {s.link.label} &darr;</a>
              ) : null}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  )
}

function ChainRow({ c }: { c: Chain }) {
  return (
    <li id={`q-${c.id}`} className="py-5 border-b scroll-mt-[calc(var(--header-h)+1rem)]"
      style={{ borderColor: 'var(--grid)' }}>
      {/* `data-short`: the question, the verdict and the sentence are the short version.
          The layers under them are not -- they are the next depth down. */}
      <div data-short="">
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Tag v={c.verdict} label={c.label} />
          <span className="text-[13.5px]" style={{ color: 'var(--text-muted)' }}>{c.question}</span>
        </p>
        <p className="text-[17px] font-semibold leading-snug mt-1.5" data-point="">
          <Said u={c.say} />
        </p>
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer inline-flex items-center gap-1.5 text-[13px]
                            font-semibold" style={{ color: 'var(--text-muted)' }}>
          <span className="conc-chev inline-block transition-transform" aria-hidden="true">
            &#9656;</span>How we know
        </summary>
        <Layers steps={c.steps} />
      </details>
    </li>
  )
}

export function BriefTop({ brief }: { brief: Brief }) {
  return (
    <section data-section="brief" className="mt-6 max-w-3xl">
      <p data-short="" data-point="" className="text-[19px] leading-snug font-semibold">
        {brief.answer.text}
      </p>

      <ol className="mt-4 border-t" style={{ borderColor: 'var(--grid)' }}>
        {brief.chains.map(c => <ChainRow key={c.id} c={c} />)}
      </ol>

    </section>
  )
}
