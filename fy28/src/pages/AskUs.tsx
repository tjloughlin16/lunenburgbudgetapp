import { useState } from 'react'
import { AskForm, type About } from '../components/AskForm'

/** Ask us a question about the budget.
 *
 *  WHAT THIS PROMISES, AND WHY IT PROMISES SO LITTLE. "A person reads every one." That is
 *  it. No timeline, no automated answer, no assurance that a given question will be
 *  answered — because the only way to keep a promise like that is to make one you can
 *  keep. Rule 7 applies to what a page says about ITSELF as much as to a figure.
 *
 *  NOTHING HERE CALLS A MODEL. The submission is stored and read later. An endpoint that
 *  asked an LLM per submission could be spammed into a bill; one that writes a row cannot,
 *  because the storage behind it does not bill at all. That is the main cost control, and
 *  it is a design decision rather than a missing feature.
 *
 *  IT FAILS CLOSED. If Turnstile is not configured, this page says the form is not
 *  accepting questions yet and does not render the box. The server refuses too, so the two
 *  agree. A form that quietly drops its bot check the moment a key goes missing is worse
 *  than one that stops working: the first failure is invisible and the second is reported
 *  the moment somebody looks.
 *
 *  ON WHAT WE ASK FOR. The question, and optionally an email. The email is optional and
 *  labelled as only being used to reply, because a budget site that requires an address
 *  before it will take a question from a resident has misunderstood who it is for.
 */

/** The page a reader came from, when they followed "Ask about this page" (AskAboutPage.tsx).
 *  Only a path on this site is taken: anything else in the address is ignored. */
function fromPage(): About | null {
  if (typeof window === 'undefined') return null
  const q = new URLSearchParams(window.location.search)
  const page = q.get('page') ?? ''
  if (!/^\/[^/]/.test(page) && page !== '/') return null
  return { page: page.slice(0, 300), title: (q.get('title') ?? '').slice(0, 160) }
}

export function AskUs() {
  const [about, setAbout] = useState(fromPage)

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Ask us a question about the budget
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Anything about the town or school budget, where the money goes, or the data on this
        site. <strong>A person reads every one.</strong>
      </p>

      <AskForm about={about} onClearAbout={() => setAbout(null)} />

      <h2 className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl">
        What happens to it
      </h2>
      <div className="max-w-2xl text-[15px] leading-relaxed space-y-3"
        style={{ color: 'var(--text-secondary)' }}>
        <p>
          It is stored and read by a person. There is no automated answer and no model is
          asked anything when you press send — partly because a machine-written answer to a
          budget question is exactly the kind of confident wrong thing this site exists to
          argue against.
        </p>
        <p>
          <strong>We cannot promise every question gets an answer</strong>, and we would
          rather say so than imply otherwise. Some will need a document the town has not
          published, in which case the honest reply is which document that is — and the
          question becomes a line on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href="/what-we-cannot-answer">what we cannot answer</a>.
        </p>
        <p>
          Your question is not published. If it becomes a page, the page answers the
          question without naming you.
        </p>
      </div>

      <h2 className="text-2xl font-bold tracking-tight mt-12 mb-3 max-w-3xl">
        What we keep
      </h2>
      <div className="max-w-2xl text-[15px] leading-relaxed space-y-3"
        style={{ color: 'var(--text-secondary)' }}>
        <p>
          The question, the topic, when it arrived, and your email if you chose to leave
          one. <strong>Not your IP address.</strong> To stop one source flooding the form we
          keep a shortened one-way hash of it, which is enough to notice a flood and not
          enough to identify anybody — a budget site holding residents&rsquo; addresses
          would be a poor trade for a rate limit.
        </p>
        <p>
          Submissions go to a database of their own, separate from the published data. That
          is a deliberate piece of plumbing: it means a flood here can never slow down or
          stale the budget data everyone else is reading.
        </p>
      </div>
    </div>
  )
}
