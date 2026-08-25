import type { Tab } from '../routes'
import { pathFor } from '../routes'
import { Note } from '../components/primitives'

/** Everything that is no longer in the reading order, kept and findable.
 *
 *  The walkthrough is a curated path through the material, not a replacement for it. Each
 *  page below still answers a question the walkthrough deliberately does not: what one
 *  specific thing costs, what a particular ranking gives up, where a figure came from.
 *  None of it is deleted, none of its URLs change, and this page exists so that none of it
 *  becomes unfindable either.
 *
 *  Grouped by the question somebody would be holding when they came looking. */
const GROUPS: { title: string; sub: string; items: { id: Tab; name: string; what: string }[] }[] = [
  {
    title: 'If you arrived with one particular question',
    sub: 'The walkthrough answers in sequence. These answer on demand.',
    items: [
      { id: 'answers', name: 'Straight answers',
        what: 'Ten questions people in Lunenburg actually ask, each answered with a number and the arithmetic that produced it. The best page here if you already know what you want to know.' },
    ],
  },
  {
    title: 'If you want a lever priced in full',
    sub: 'The walkthrough shows one chart from each of these. This is the rest of the argument.',
    items: [
      { id: 'money', name: 'Find the money',
        what: 'Pick a number — $500,000, $1M, $2M — and see what raising it takes on every lever at once, with no projection involved. Including the several that cannot reach it at any price.' },
      { id: 'override', name: 'Overrides',
        what: 'How big, for how long, and written for whom. What an override actually is, what one buys, why it is not one vote, and what a single question sized to last would cost.' },
      { id: 'development', name: 'Development',
        what: 'Commercial and residential build rates as dials, with what each does to the town’s revenue, the school gap and the balance between homeowners and business.' },
    ],
  },
  {
    title: 'If you want the mechanism',
    sub: 'Why the gap reopens every year, and what it would take to stop it.',
    items: [
      { id: 'why', name: 'Why it repeats',
        what: 'The original written version of the two-rates argument, before it became something you could operate. Longer, more detailed, and the place where the cut cascade is worked out to its end.' },
      { id: 'curve', name: 'Bend the curve',
        what: 'The full rate page. Everything in the walkthrough’s middle rooms, plus the leverage ranking, six futures priced side by side, what permanent balance requires, and what the state would have to do.' },
    ],
  },
  {
    title: 'If you want to decide it yourself',
    sub: 'The walkthrough refuses to say what should go. These do not.',
    items: [
      { id: 'priorities', name: 'Priorities',
        what: 'Set the order things are given up in, and watch the cascade run year by year until the list runs out. Answers “in what order”, which the walkthrough leaves open on purpose.' },
      { id: 'adjust', name: 'Build your own budget',
        what: 'Every dial that moves the gap, on one page, with a running total. The page to bring to a meeting.' },
    ],
  },
  {
    title: 'If you do not believe a number',
    sub: 'Which is the right instinct, and the reason this page exists.',
    items: [
      { id: 'context', name: 'The situation',
        what: 'What happened, what it costs, and where every figure comes from — the published documents, the line-by-line derivations, and the reconciliations that show the model rebuilding the town’s own totals.' },
    ],
  },
]

export function GoDeeper({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-4">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Everything else</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Go deeper
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          The walkthrough is one path through this material, chosen to be followed in order
          by somebody who has never opened a budget document. It is not all of it. Every
          page below answers something the walkthrough deliberately leaves alone.
        </p>
        <Note>
          Nothing here has been retired and no address has changed. If you have a link to
          one of these pages it still works.
        </Note>
      </div>

      {GROUPS.map(g => (
        <section key={g.title} className="border-t py-10" style={{ borderColor: 'var(--grid)' }}>
          <div className="mx-auto max-w-6xl px-5">
            <h2 className="text-[17px] font-bold">{g.title}</h2>
            <p className="text-[13px] mb-5" style={{ color: 'var(--text-muted)' }}>{g.sub}</p>
            <div className="grid gap-3 lg:grid-cols-2 items-start">
              {g.items.map(it => (
                <button key={it.id} onClick={() => onJump(it.id)}
                  className="card p-4 text-left w-full transition-opacity hover:opacity-90">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[15px] font-bold">{it.name}</span>
                    <span className="text-[11px] tnum shrink-0"
                      style={{ color: 'var(--text-muted)' }}>{pathFor(it.id)}</span>
                  </div>
                  <span className="block text-[13px] leading-relaxed mt-1.5"
                    style={{ color: 'var(--text-secondary)' }}>{it.what}</span>
                  <span className="block text-[12px] font-semibold mt-2.5"
                    style={{ color: 'var(--series-cost)' }}>Open &rarr;</span>
                </button>
              ))}
            </div>
          </div>
        </section>
      ))}
    </div>
  )
}
