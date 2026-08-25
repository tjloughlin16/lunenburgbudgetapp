import { MODEL, project, usd } from '../model/engine'
import { Section, Note } from '../components/primitives'
import { Structural } from '../components/Structural'

/** The root cause, given its own tab.
 *
 *  It sat as one section inside the situation page and nobody found it, which is a fair
 *  verdict on burying the explanation for everything else three screens down. This is the
 *  answer to "why did we close a gap this year and have a bigger one coming", and it is the
 *  argument the other three tabs are downstream of. */
export function WhyItRepeats() {
  const gap = project(5, MODEL.assumptions)[0].deficit

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The root cause</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Why this keeps happening
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Lunenburg closed a budget gap for the year it is in, and a bigger one opens next
          year.
          That is not mismanagement and it is not bad luck &mdash; it is arithmetic that
          was always going to produce this, and it will produce it again next year, and the
          year after. Here is the mechanism, what each way out is genuinely worth, and why
          cutting stops being available at all in about six years.
        </p>
        <Note>
          Everything on this page runs on the district&rsquo;s own published growth rates
          and the same cut cascade as the Priorities tab. The FY28 gap it starts from is{' '}
          {usd(gap)}.
        </Note>
      </div>

      <Section id="mechanism" eyebrow="The arithmetic"
        title="Two growth rates that were never going to meet">
        <Structural />
      </Section>
    </div>
  )
}
