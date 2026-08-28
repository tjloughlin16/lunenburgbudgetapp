import { SourceIndex } from '../components/SourceIndex'
import type { Tab } from '../routes'

/** Every document, at its own address.
 *
 *  This began as a section inside The situation, three clicks and a scroll from the front
 *  door, which is the wrong place for it. The whole argument of this site is that a
 *  resident can check it, and burying the evidence four levels down contradicts that
 *  claim more effectively than any disclaimer repairs it.
 *
 *  So it is top level, it is in the header on every page, it is the first line of the
 *  footer on every page, and the address is /sources — short enough to say out loud in a
 *  meeting, which is where somebody is standing when they need it. */
export function Sources({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-8">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Check us</p>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
          Every document this is built on
        </h1>
        <p className="mt-5 text-lg leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          This site asks you to accept a lot of arithmetic about your own tax bill. The
          honest answer to &ldquo;says who?&rdquo; is not a paragraph promising the sources
          are public &mdash; it is the list. Here it is, including the documents that turned
          out to be unreadable and the ones that say something inconvenient.
        </p>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Nothing here was obtained by request or paid for. All of it is published by the
          school district, the town, the state, or a neighbouring district, and every one
          can be found again from the links below. If a number on this site does not match
          a document here, the document is right.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button onClick={() => onJump('context')}
            className="text-xs font-semibold px-3 py-2 rounded-md"
            style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
            Where the numbers come from &rarr;
          </button>
          <button onClick={() => onJump('deeper')}
            className="text-xs font-semibold px-3 py-2 rounded-md"
            style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            Every other page &rarr;
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5 pb-16">
        <SourceIndex />

        {/* Said out loud rather than hidden in a comment for machines. If somebody is
            checking this site with an assistant, the assistant should be pointed at the
            structured data — and the reader should be able to see that we did it. */}
        <div className="card p-5 mt-8">
          <h3 className="text-[15px] font-bold mb-2">Checking this with an AI assistant?</h3>
          <p className="text-[13.5px] leading-relaxed max-w-3xl mb-3"
            style={{ color: 'var(--text-secondary)' }}>
            Point it at <a href="/llms.txt" className="underline"
              style={{ color: 'var(--series-cost)' }}>lunenburgbudgetproject.org/llms.txt</a>.
            That page explains what data exists, where every file lives, and the one thing
            most likely to be got wrong &mdash; that this archive holds both what the town{' '}
            <em>budgeted</em> and what it <em>spent</em>, which differ by up to 59% on some
            lines and must never be combined in a single calculation.
          </p>
          <p className="text-[12.5px] leading-relaxed max-w-3xl"
            style={{ color: 'var(--text-muted)' }}>
            The underlying data is downloadable directly:{' '}
            {[['model.json', 'every figure the site computes'],
              ['sources.json', 'the document archive'],
              ['budget-lines.csv', 'the district budget, 351 lines'],
              ['district-page-index.csv', '87 mirrored district documents'],
              ['minutes-index.csv', '1,422 town meeting records']].map(([f, w], i) => (
              <span key={f}>{i > 0 ? ' · ' : ''}
                <a href={`/data/${f}`} download className="underline"
                  style={{ color: 'var(--text-secondary)' }}>{f}</a>{' '}({w})
              </span>
            ))}.
          </p>
        </div>
      </div>
    </div>
  )
}
