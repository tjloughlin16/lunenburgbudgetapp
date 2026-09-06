import MANIFEST from '../data/agent-manifest.json'

/** The machine-readable addresses, at the TOP of the document.
 *
 *  WHY THE TOP, WHEN THE FOOTER ALREADY HAS THEM
 *
 *  Because the footer is not delivered. Measured on the production front page: it is
 *  255,823 bytes, and `href="/api/index"` sits at byte 243,571 -- **95.2% of the way
 *  through**. A reader that converts a page and caps the result never reaches it. That is
 *  not a guess: `/api/lines`, 121KB of JSON, comes back from a fetch tool truncated
 *  mid-record, so the ceiling is well under this page's size.
 *
 *  So an assistant read this site, was told by `llms.txt` that `/api/index` exists, and
 *  could not fetch it -- its own words: *"the fetch tool is refusing every URL on the site
 *  except the two I already pulled... it isn't registering the ones inside llms.txt."*
 *  Both halves were true at once. The links were live and unreachable.
 *
 *  `llms.txt` cannot fix this, ever. It is `text/plain`, so the addresses in it are text
 *  rather than links, and a reader that only fetches URLs it has seen linked is not
 *  authorised by it. **The only route into the link graph is an HTML page, and the links
 *  have to be early enough in one to survive the cut.** This line lands inside the first
 *  couple of KB of converted text on every route.
 *
 *  It is small, visible and honest -- not hidden, for the reasons in DataFooter.tsx: text
 *  served only to machines is cloaking, and it would not work anyway, because the readers
 *  that matter drop hidden nodes exactly as they drop comments.
 *
 *  `scripts/agent-view.mjs --links` fails the build if any of these drifts past 50,000
 *  characters of converted text, so this cannot quietly slide down the page again. */
/* Absolute. This line is the first machine-readable address on the page, put there
 * because /api/index used to sit 95% of the way down the homepage; a relative href
 * makes it unusable to the caller it was moved up for. */
const ABS = (p: string) => `${MANIFEST.site}${p}`

export function DataTopLine() {
  const host = MANIFEST.site.replace(/^https?:\/\//, '')
  const link = (p: string, label?: string) => (
    <a href={ABS(p)} className="underline underline-offset-2"
       style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
      {label ?? `${host}${p}`}
    </a>
  )
  return (
    <div className="border-b" style={{ borderColor: 'var(--grid)' }}>
      <p className="mx-auto max-w-6xl px-5 py-1.5 text-[11px] leading-snug"
         style={{ color: 'var(--text-muted)' }}>
        <strong style={{ color: 'var(--text-secondary)' }}>Reading this with software?</strong>{' '}
        Every figure and document here is downloadable. {link('/mcp')} is an MCP server ·{' '}
        {link('/api/index')} is the data API · {link('/llms.txt')} explains them ·{' '}
        {link('/agents')} lists every address as a link · {link('/minutes/INDEX.txt')} is
        the meeting archive.
      </p>
    </div>
  )
}
