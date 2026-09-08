import { useEffect, useRef, useState } from 'react'
import CONFIG from '../data/ask-config.json'

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

type Status = 'idle' | 'sending' | 'sent' | 'error'

const TOPICS: { value: string; label: string }[] = [
  { value: '', label: 'Not sure' },
  { value: 'schools', label: 'The school budget' },
  { value: 'town', label: 'The town budget' },
  { value: 'taxes', label: 'Taxes and the levy' },
  { value: 'data', label: 'The data on this site' },
  { value: 'other', label: 'Something else' },
]

declare global {
  interface Window { turnstile?: { render: (el: HTMLElement, o: Record<string, unknown>) => string } }
}

export function AskUs() {
  const [question, setQuestion] = useState('')
  const [email, setEmail] = useState('')
  const [topic, setTopic] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const widget = useRef<HTMLDivElement | null>(null)
  const rendered = useRef(false)

  const siteKey = (CONFIG as { turnstileSiteKey?: string }).turnstileSiteKey || ''

  /** THE SERVER DECIDES WHETHER THIS FORM IS OPEN, not this page.
   *
   *  The site key is here and the secret is only in Cloudflare, so the two halves can
   *  disagree — and once did: the key was set while the secret was not, which would have
   *  rendered a form that looked live and refused every submission. A person only finds
   *  that out after writing their question, which is the worst moment to find it out.
   *
   *  `null` while we are asking. The form does not render on a guess. */
  const [accepting, setAccepting] = useState<boolean | null>(null)
  useEffect(() => {
    let alive = true
    fetch('/api/ask')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(j => { if (alive) setAccepting(Boolean(j.accepting)) })
      .catch(() => { if (alive) setAccepting(false) })
    return () => { alive = false }
  }, [])

  const live = Boolean(siteKey) && accepting === true

  useEffect(() => {
    if (!live || rendered.current) return
    const s = document.createElement('script')
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    s.async = true
    s.onload = () => {
      if (!widget.current || rendered.current || !window.turnstile) return
      rendered.current = true
      window.turnstile.render(widget.current, {
        sitekey: siteKey,
        callback: (t: string) => setToken(t),
        'expired-callback': () => setToken(null),
        'error-callback': () => setToken(null),
      })
    }
    document.head.appendChild(s)
  }, [live, siteKey])

  const left = 2000 - question.length
  const canSend = question.trim().length >= 10 && left >= 0 && status !== 'sending'

  async function send(e: React.FormEvent) {
    e.preventDefault()
    setStatus('sending'); setError(null)
    try {
      const r = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ question: question.trim(), email: email.trim(), topic, token }),
      })
      const j = await r.json()
      if (!r.ok || !j.ok) { setStatus('error'); setError(j.error || `HTTP ${r.status}`); return }
      setStatus('sent'); setQuestion(''); setEmail('')
    } catch (err) {
      setStatus('error'); setError(String(err))
    }
  }

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

      {status === 'sent' ? (
        <div className="card p-6 mt-8 max-w-2xl"
          style={{ borderLeft: '4px solid var(--series-cost)' }}>
          <p className="text-[17px] font-bold">Got it — thank you.</p>
          <p className="text-[14.5px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            It is in the queue. If you left an email we will use it only to reply. If the
            answer turns out to be something this site should explain properly, it becomes
            a page and you will have made the site better.
          </p>
          <button onClick={() => setStatus('idle')}
            className="mt-4 text-[14px] font-semibold underline"
            style={{ color: 'var(--series-cost)' }}>Ask another</button>
        </div>
      ) : accepting === null ? (
        <p className="mt-8 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Checking whether the form is open&hellip;
        </p>
      ) : !live ? (
        <div className="card p-6 mt-8 max-w-2xl"
          style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[17px] font-bold">Not accepting questions just yet</p>
          <p className="text-[14.5px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            The spam check is not configured on this build, so the form is switched off
            rather than left open. Nothing you type here would be saved, so it is not
            shown at all.
          </p>
        </div>
      ) : (
        <form onSubmit={send} className="card p-5 sm:p-6 mt-8 max-w-2xl">
          <label className="block text-[13px] font-semibold uppercase tracking-wider mb-2"
            style={{ color: 'var(--text-muted)' }}>Your question</label>
          <textarea
            value={question} onChange={e => setQuestion(e.target.value)} rows={6}
            placeholder="For example: why did the school budget have a surplus, and where did it sit?"
            className="w-full rounded-md px-3 py-2.5 text-[15px] leading-relaxed"
            style={{ background: 'var(--bg)', color: 'var(--text-primary)',
                     border: '1px solid var(--grid)' }} />
          <div className="flex justify-between items-baseline mt-1.5">
            <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              At least 10 characters.
            </span>
            <span className="text-[12px] tnum"
              style={{ color: left < 0 ? 'var(--status-warning)' : 'var(--text-muted)' }}>
              {left.toLocaleString()} left
            </span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 mt-5">
            <div>
              <label className="block text-[13px] font-semibold uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-muted)' }}>Roughly about</label>
              <select value={topic} onChange={e => setTopic(e.target.value)}
                className="w-full rounded-md px-3 py-2.5 text-[15px]"
                style={{ background: 'var(--bg)', color: 'var(--text-primary)',
                         border: '1px solid var(--grid)' }}>
                {TOPICS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[13px] font-semibold uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-muted)' }}>Email — optional</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="only so we can reply"
                className="w-full rounded-md px-3 py-2.5 text-[15px]"
                style={{ background: 'var(--bg)', color: 'var(--text-primary)',
                         border: '1px solid var(--grid)' }} />
            </div>
          </div>

          <div ref={widget} className="mt-5" />

          <button type="submit" disabled={!canSend}
            className="mt-5 px-5 py-3 rounded-md text-[15px] font-bold min-h-[44px]
                       transition-opacity disabled:opacity-40"
            style={{ background: 'var(--series-cost)', color: 'var(--bg)' }}>
            {status === 'sending' ? 'Sending…' : 'Send the question'}
          </button>

          {error && (
            <p className="text-[13.5px] mt-3" style={{ color: 'var(--status-warning)' }}>
              {error}
            </p>
          )}
        </form>
      )}

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
