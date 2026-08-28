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
      </div>
    </div>
  )
}
