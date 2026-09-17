import { useEffect } from 'react'

/** A FEED, ANNOUNCED TWICE: once in the head, so a feed reader pointed at this page's
 *  URL finds it on its own (autodiscovery), and once on the page, so a person does.
 *
 *  TJ, 17 September 2026: "I specifically want them to be able to get updates when an
 *  individual board gets updated with a meeting, or something like the budget feed
 *  updates." The feeds are static files scripts/build_feeds.py regenerates with every
 *  refresh; this site holds no subscriber list. Email is offered through an
 *  RSS-to-email service rather than built here, for the same reason the analytics keep
 *  no identifier: the project should not be holding residents' addresses.
 *
 *  The head link is added in an effect, and the prerenderer captures the DOM after
 *  effects run, so the tag is in the static HTML a reader fetches. */
export function useFeedLink(path: string | null, title: string) {
  useEffect(() => {
    if (!path) return
    const el = document.createElement('link')
    el.rel = 'alternate'
    el.type = 'application/atom+xml'
    el.title = title
    el.href = path
    document.head.appendChild(el)
    return () => { el.remove() }
  }, [path, title])
}

export function Subscribe({ path, what }: { path: string; what: string }) {
  const url = `${window.location.origin}${path}`
  return (
    <p className="text-[13px] leading-relaxed mt-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
      <strong style={{ color: 'var(--text-primary)' }}>Get told when {what}.</strong>{' '}
      This page has a feed: <a className="underline break-all" href={path}>{url}</a>. Paste it into
      any feed reader, or into a free feed-to-email service such as{' '}
      <a className="underline" href="https://feedrabbit.com" rel="noopener">Feedrabbit</a> or{' '}
      <a className="underline" href="https://blogtrottr.com" rel="noopener">Blogtrottr</a> to get it
      as email. No account here, and nothing about you is recorded.
    </p>
  )
}
