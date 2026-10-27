import { useEffect, useRef, useState } from 'react'
import { track } from '../lib/track'
import CONFIG from '../data/ask-config.json'

/** The question form, shared by the question page (pages/AskUs.tsx) and the "Ask about
 *  this page" drawer (AskAboutPage.tsx). One form, so the two cannot drift: the page's
 *  promises -- a person reads every one, it fails closed without the spam check -- are
 *  this component's, wherever it is drawn. */

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

export type About = { page: string; title: string }

export function AskForm({ about, onClearAbout }: { about: About | null; onClearAbout: () => void }) {
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
    const draw = () => {
      if (!widget.current || rendered.current || !window.turnstile) return
      rendered.current = true
      window.turnstile.render(widget.current, {
        sitekey: siteKey,
        callback: (t: string) => setToken(t),
        'expired-callback': () => setToken(null),
        'error-callback': () => setToken(null),
      })
    }
    // The drawer can open many times on one page: load the script once, draw each time.
    if (window.turnstile) { draw(); return }
    const s = document.createElement('script')
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    s.async = true
    s.onload = draw
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
        body: JSON.stringify({ question: question.trim(), email: email.trim(), topic, token,
                               page: about?.page ?? '', page_title: about?.title ?? '' }),
      })
      const j = await r.json()
      if (!r.ok || !j.ok) { setStatus('error'); setError(j.error || `HTTP ${r.status}`); return }
      setStatus('sent'); setQuestion(''); setEmail('')
      track('question')
    } catch (err) {
      setStatus('error'); setError(String(err))
    }
  }

  return (<>
  {about && (
    <div className="card flex items-baseline justify-between gap-3 mt-8 max-w-2xl px-5 py-3 text-[14.5px]"
      style={{ borderLeft: '4px solid var(--series-cost)' }}>
      <span style={{ color: 'var(--text-secondary)' }}>
        About the page{' '}
        <a href={about.page} className="font-semibold underline"
          style={{ color: 'var(--series-cost)' }}>{about.title || about.page}</a>
      </span>
      <button type="button" onClick={onClearAbout}
        className="text-[12.5px] underline shrink-0" style={{ color: 'var(--text-muted)' }}>
        Not about this page
      </button>
    </div>
  )}

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
        placeholder={about
          ? 'What is confusing, missing or looks wrong on this page?'
          : 'For example: why did the school budget have a surplus, and where did it sit?'}
        className="w-full rounded-md px-3 py-2.5 text-[15px] leading-relaxed"
        style={{ background: 'var(--surface-1)', color: 'var(--text-primary)',
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
            style={{ background: 'var(--surface-1)', color: 'var(--text-primary)',
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
            style={{ background: 'var(--surface-1)', color: 'var(--text-primary)',
                     border: '1px solid var(--grid)' }} />
        </div>
      </div>

      <div ref={widget} className="mt-5" />

      <button type="submit" disabled={!canSend}
        className="mt-5 px-5 py-3 rounded-md text-[15px] font-bold min-h-[44px]
                   transition-opacity disabled:opacity-40"
        style={{ background: 'var(--series-cost)', color: 'var(--surface-1)' }}>
        {status === 'sending' ? 'Sending…' : 'Send the question'}
      </button>

      {error && (
        <p className="text-[13.5px] mt-3" style={{ color: 'var(--status-warning)' }}>
          {error}
        </p>
      )}
    </form>
  )}
  </>)
}
