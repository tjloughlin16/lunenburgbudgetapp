const BTN = 'inline-flex items-center rounded-lg px-3 py-2 text-[14px] font-medium'
const BTN_STYLE = { border: '1px solid var(--grid)', color: 'var(--link, var(--text-primary))' }

/** THE 404. An address nothing on the site answers renders this, inside the ordinary header
 *  and footer, instead of the front page. TJ, 19 October 2026: "redirecting to HOME is very
 *  confusing". It says what happened, shows the address that failed, and offers a search
 *  already filled with the words in that address -- a renamed report is usually one search
 *  away from its old slug. */
export default function NotFound() {
  const path = window.location.pathname
  const words = path.replace(/^\/+|\/+$/g, '').split(/[/\-_.]+/).filter(Boolean).join(' ')
  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <p className="text-[12px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>404</p>
      <h1 className="text-3xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>
        Page not found</h1>
      <p className="mt-3 text-[15px]" style={{ color: 'var(--text-secondary)' }}>
        Nothing on this site lives at <code className="break-all">{path}</code>. The link may be
        mistyped, or the page may have moved.</p>
      <div className="flex flex-wrap gap-3 mt-6">
        {words ? <a className={BTN} style={BTN_STYLE} href={`/search?q=${encodeURIComponent(words)}`}>
          Search for “{words}”</a> : null}
        <a className={BTN} style={BTN_STYLE} href="/reports">All reports</a>
        <a className={BTN} style={BTN_STYLE} href="/">Home</a>
      </div>
    </main>
  )
}
